import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    CategoricalParameter,
    merge_informative_pair,
)
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_minutes
# from indicators import calculate_all_indicators
import warnings
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

class NewsHeliusBitqueryML(IStrategy):
    timeframe = "15m"
    informative_timeframe = "1h"
    can_short = False
    process_only_new_candles = True
    startup_candle_count = 50
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    position_adjustment_enable = False
    order_time_in_force = {
        "entry": "GTC",
        "exit": "GTC"
    }
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "limit",
        "stoploss_on_exchange": False,
        "stoploss_on_exchange_interval": 60,
    }
    
    # Параметры для гипероптимизации ROI
    minimal_roi = {
        "0": 0.006,
        "30": 0.003,
        "90": 0.0
    }
    
    stoploss = -0.012
    
    trailing_stop = True
    trailing_stop_positive = 0.004
    trailing_stop_positive_offset = 0.010
    trailing_only_offset_is_reached = True
    
    ignore_buying_expired_candle_after = 1
    
    # --- ПАРАМЕТРЫ ВХОДА / ФИЛЬТРОВ ---
    donch_window = IntParameter(20, 60, default=40, space="buy", optimize=True)
    atr_min_pct = DecimalParameter(0.0020, 0.0100, decimals=4, default=0.0045, space="buy", optimize=True)
    rsi_min_long = IntParameter(48, 58, default=52, space="buy", optimize=True)
    adx_min = IntParameter(14, 28, default=20, space="buy", optimize=True)
    ema_kiss_pct = DecimalParameter(0.0010, 0.0040, decimals=4, default=0.0020, space="buy", optimize=True)

    entry_mode = CategoricalParameter(["breakout", "pullback"], default="breakout", space="buy", optimize=True)

    # --- ПАРАМЕТРЫ ВЫХОДА / РИСК ---
    rsi_exit_high = IntParameter(62, 75, default=68, space="sell", optimize=True)
    sl_static = DecimalParameter(-0.025, -0.008, decimals=3, default=-0.012, space="protection", optimize=True)
    ts_enable = CategoricalParameter([True, False], default=True, space="sell", optimize=True)
    ts_positive = DecimalParameter(0.0030, 0.0100, decimals=4, default=0.0060, space="sell", optimize=True)
    ts_offset = DecimalParameter(0.0060, 0.0200, decimals=4, default=0.0100, space="sell", optimize=True)

    def __init__(self, config: dict = None) -> None:
        super().__init__(config)
        # Подключаем SL/TS к параметрам
        try:
            self.stoploss = float(self.sl_static.value)
            self.trailing_stop = bool(self.ts_enable.value)
            self.trailing_stop_positive = float(self.ts_positive.value)
            self.trailing_stop_positive_offset = float(self.ts_offset.value)
            self.trailing_only_offset_is_reached = True
        except Exception:
            # В случаях, когда параметры ещё не инициализированы (например, документация или статический анализ)
            pass

    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        # --- EMA(50/200)
        df["ema_fast"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=200, adjust=False).mean()
        # Слоупы ЕМА (направление тренда)
        df["ema_fast_slope"] = df["ema_fast"] - df["ema_fast"].shift(1)

        # --- MACD (12,26,9)
        macd_fast = df["close"].ewm(span=12, adjust=False).mean()
        macd_slow = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = macd_fast - macd_slow
        df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_sig"]
        # Слоуп гистограммы (ускорение)
        df["macd_hist_slope"] = df["macd_hist"] - df["macd_hist"].shift(1)

        # --- RSI (14) по Уайлдеру
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        rs = avg_gain / (avg_loss.replace(0, np.nan))
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50)

        # --- ATR(14) и волатильность
        prev_close = df["close"].shift(1)
        tr = np.maximum(df["high"] - df["low"],
                        np.maximum((df["high"] - prev_close).abs(),
                                   (df["low"] - prev_close).abs()))
        df["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
        
        # 1) Расчёт ATR% (диапазон волатильности)
        df["atr_pct"] = (df["atr"] / df["close"]).clip(lower=0)
        # Фильтр волатильности: ATR% > заданного минимума
        df["vol_ok"] = df["atr_pct"] > float(self.atr_min_pct.value)
        
        # --- Donchian Channels для breakout режима (по параметру окна)
        win = int(self.donch_window.value)
        df["donch_hi"] = df["high"].rolling(win, min_periods=win).max()
        df["donch_lo"] = df["low"].rolling(win, min_periods=win).min()

        # --- ADX(14) для фильтра силы тренда
        up_move = df["high"].diff()
        down_move = -df["low"].diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        tr_components = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ], axis=1)
        tr14 = tr_components.max(axis=1).ewm(alpha=1/14, adjust=False).mean()
        plus_di = 100 * (pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / tr14)
        minus_di = 100 * (pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / tr14)
        dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).replace([np.inf, -np.inf], np.nan)
        df["adx"] = dx.ewm(alpha=1/14, adjust=False).mean().fillna(20)

        # 2) Информативные данные 1h: EMA200_1h и её наклон
        try:
            pair = metadata.get("pair") if isinstance(metadata, dict) else None
            if pair and hasattr(self, "dp") and self.dp:
                inf_df = self.dp.get_pair_dataframe(pair=pair, timeframe=self.informative_timeframe)
                if not inf_df.empty:
                    inf_df = inf_df.copy()
                    inf_df["ema200"] = inf_df["close"].ewm(span=200, adjust=False).mean()
                    inf_df["ema200_slope"] = inf_df["ema200"].pct_change(3)
                    df = merge_informative_pair(
                        dataframe=df,
                        informative=inf_df[["date", "ema200", "ema200_slope"]],
                        timeframe=self.timeframe,
                        timeframe_inf=self.informative_timeframe,
                        ffill=True,
                    )
                    # Режимный фильтр по 1h EMA200
                    df["regime_long"] = (df["close"] > df["ema200_1h"]) & (df["ema200_slope_1h"] > 0)
                    df["regime_short"] = (df["close"] < df["ema200_1h"]) & (df["ema200_slope_1h"] < 0)
        except Exception:
            # В случае отсутствия dp или на самых ранних свечах — безопасный дефолт
            df["regime_long"] = True
            df["regime_short"] = False

        # безопасность от NaN
        for c in [
            "ema200_1h",
            "ema200_slope_1h",
            "regime_long",
            "regime_short",
            "atr_pct",
            "vol_ok",
            "donch_hi",
            "donch_lo",
            "adx",
        ]:
            if c in df:
                df[c] = df[c].ffill().bfill()

        # --- чистка
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        return df

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Режим входа
        mode = self.entry_mode.value if isinstance(self.entry_mode, CategoricalParameter) else "breakout"

        vol_ok = df.get("vol_ok", pd.Series(True, index=df.index))
        regime_long = df.get("regime_long", pd.Series(True, index=df.index))

        if mode == "breakout":
            # Пробой Donchian High (окно параметризовано) + RSI/ADX + режимный фильтр
            donch_hi_prev = df["donch_hi"].shift(1)
            long_cond = (
                vol_ok
                & (df["close"] > donch_hi_prev)
                & (df["rsi"] > int(self.rsi_min_long.value))
                & (df["adx"] > int(self.adx_min.value))
                & regime_long
            )
            short_cond = pd.Series(False, index=df.index)
        else:
            # Откат: цена в пределах ± ema_kiss_pct от EMA_fast + подтверждение MACD-гистограммой + режимный фильтр
            near_ema = (df["close"] / df["ema_fast"] - 1.0).abs() <= float(self.ema_kiss_pct.value)
            macd_conf = (df["macd_hist"] > 0) & (df["macd_hist_slope"] > 0)
            long_cond = vol_ok & near_ema & macd_conf & regime_long
            short_cond = pd.Series(False, index=df.index)

        # Итоговые сигналы
        df["enter_long"] = 0
        df["enter_short"] = 0
        df.loc[long_cond, "enter_long"] = 1
        df.loc[short_cond, "enter_short"] = 1

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Выход: RSI выше порога или пробой вниз EMA_fast
        exit_l = (df["rsi"] > int(self.rsi_exit_high.value)) | (df["close"] < df["ema_fast"]) 
        exit_s = pd.Series(False, index=df.index)

        df["exit_long"] = 0
        df["exit_short"] = 0
        df.loc[exit_l, "exit_long"] = 1
        df.loc[exit_s, "exit_short"] = 1
        return df
    
    def informative_pairs(self):
        # используем те же пары на 1h
        try:
            return [(pair, self.informative_timeframe) for pair in self.dp.current_whitelist()]
        except Exception:
            return []

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 5},
            {"method": "StoplossGuard", "lookback_period_candles": 144, "trade_limit": 2, "stop_duration_candles": 30, "only_per_pair": True},
            {"method": "MaxDrawdown", "lookback_period_candles": 288, "trade_limit": 20, "stop_duration_candles": 60, "max_allowed_drawdown": 0.08}
        ]