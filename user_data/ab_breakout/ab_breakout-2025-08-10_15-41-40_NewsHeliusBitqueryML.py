import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, merge_informative_pair
from freqtrade.strategy.parameters import CategoricalParameter
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_minutes
# from indicators import calculate_all_indicators
import warnings
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

class NewsHeliusBitqueryML(IStrategy):
    timeframe = "5m"
    informative_timeframe = "1h"
    can_short = True
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
    
    # Параметр режима входа
    entry_mode = CategoricalParameter(["breakout", "pullback"], default="breakout", space="buy", optimize=True)
    
    # Параметры для гипероптимизации
    buy_params = {
        "vol_min": 0.002,
        "rsi_long_th": 45,
        "adx_min": 14,
        "ema_fast": 12,
        "ema_slow": 26,
        "rsi_period": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "atr_period": 14
    }
    
    sell_params = {
        "rsi_exit_long": 70,
        "ema_exit_long": True
    }
    
    # Параметры для гипероптимизации ROI
    roi_params = {
        "roi_0": 0.006,
        "roi_30": 0.003,
        "roi_90": 0.0
    }
    
    # Параметры для гипероптимизации Stoploss
    stoploss_params = {
        "stoploss": -0.012
    }
    
    # Параметры для гипероптимизации Trailing Stop
    trailing_params = {
        "trailing_stop": True,
        "trailing_stop_positive": 0.004,
        "trailing_stop_positive_offset": 0.010,
        "trailing_only_offset_is_reached": True
    }

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
        # нижний и верхний пороги волатильности (очень упрощено для тестирования)
        df["vol_ok"] = (df["atr_pct"] >= 0.0001) & (df["atr_pct"] <= 0.100)
        
        # --- Donchian Channels для breakout режима
        df["donch_hi"] = df["high"].rolling(20, min_periods=20).max()
        df["donch_lo"] = df["low"].rolling(20, min_periods=20).min()

        # 2) Временно используем 5m данные вместо 1h для режимных фильтров
        df["ema200_5m"] = df["close"].ewm(span=200, adjust=False).mean()
        df["ema200_5m_slope"] = df["ema200_5m"].pct_change(5)  # наклон за ~25 минут

        # 3) Режимные фильтры
        df["regime_long"]  = (df["close"] > df["ema200_5m"]) & (df["ema200_5m_slope"] > 0)
        df["regime_short"] = (df["close"] < df["ema200_5m"]) & (df["ema200_5m_slope"] < 0)

        # безопасность от NaN
        for c in ["ema200_5m", "ema200_5m_slope", "regime_long", "regime_short", "atr_pct", "vol_ok", "donch_hi", "donch_lo"]:
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

        # Базовый фильтр волатильности, чтобы избежать сверхтихих участков
        vol_ok = df.get("vol_ok", pd.Series(True, index=df.index))

        if mode == "breakout":
            # Пробой Donchian 20 c отставанием на 1 свечу
            donch_hi = df.get("donch_hi", df["high"].rolling(20, min_periods=20).max())
            donch_lo = df.get("donch_lo", df["low"].rolling(20, min_periods=20).min())
            donch_hi_prev = donch_hi.shift(1)
            donch_lo_prev = donch_lo.shift(1)

            long_cond = vol_ok & (df["close"] > donch_hi_prev)
            short_cond = vol_ok & (df["close"] < donch_lo_prev)
        else:
            # Откат к EMA(50) с направлением по RSI
            ema_fast = df.get("ema_fast", df["close"].ewm(span=50, adjust=False).mean())
            near_ema = (df["close"] / ema_fast - 1.0).abs() <= 0.01  # 1%

            rsi = df.get("rsi", pd.Series(50, index=df.index))
            long_cond = vol_ok & near_ema & (rsi > 50)
            short_cond = vol_ok & near_ema & (rsi < 50)

        # Итоговые сигналы
        df["enter_long"] = 0
        df["enter_short"] = 0
        df.loc[long_cond, "enter_long"] = 1
        df.loc[short_cond, "enter_short"] = 1

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Выходим, когда импульс тухнет или сигнал разворота
        exit_l = (
            (df["rsi"] > 68) |
            (df["macd_hist"] < 0) |
            (df["close"] < df["ema_fast"])
        )
        exit_s = (
            (df["rsi"] < 32) |
            (df["macd_hist"] > 0) |
            (df["close"] > df["ema_fast"])
        )

        df["exit_long"] = 0
        df["exit_short"] = 0
        df.loc[exit_l, "exit_long"] = 1
        df.loc[exit_s, "exit_short"] = 1
        return df
    
    def informative_pairs(self):
        # используем те же пары на 1h
        return [(pair, self.informative_timeframe) for pair in self.dp.current_whitelist()]
    
    # Методы для гипероптимизации ROI
    def custom_roi(self, dataframe: DataFrame, trade: Trade, current_time: datetime, **kwargs) -> float:
        # Динамический ROI на основе времени удержания позиции
        open_minutes = (current_time - trade.open_date_utc).total_seconds() / 60
        
        if open_minutes <= 30:
            return self.roi_params['roi_0']
        elif open_minutes <= 90:
            return self.roi_params['roi_30']
        else:
            return self.roi_params['roi_90']
    
    # Методы для гипероптимизации Stoploss
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        return self.stoploss_params['stoploss']
    
    # Методы для гипероптимизации Trailing Stop
    def custom_trailing_stop(self, pair: str, trade: Trade, current_time: datetime, current_rate: float, current_profit: float, **kwargs) -> float:
        if not self.trailing_params['trailing_stop']:
            return 0
        
        if current_profit > self.trailing_params['trailing_stop_positive_offset']:
            return self.trailing_params['trailing_stop_positive']
        
        return 0

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 5},
            {"method": "StoplossGuard", "lookback_period_candles": 288,
             "stop_duration_candles": 30, "only_per_pair": False, "trade_limit": 2},
            {"method": "MaxDrawdown", "lookback_period_candles": 288,
             "stop_duration_candles": 60, "max_allowed_drawdown": 8,
             "only_per_pair": False}
        ]