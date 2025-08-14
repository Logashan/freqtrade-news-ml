import logging
from typing import Dict

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter


logger = logging.getLogger(__name__)


class IntradayScalp5m(IStrategy):
    timeframe = "5m"
    can_short = True
    process_only_new_candles = True
    # Должно покрывать объёмный квантиль и Keltner
    startup_candle_count = 320

    # Короткая лесенка ROI (будет переоптимизировано hyperopt'ом)
    minimal_roi = {"0": 0.006, "15": 0.004, "45": 0.002, "90": 0.0}

    # Типы ордеров
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "limit",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_interval": 60,
        "stoploss_on_exchange_limit_ratio": 0.99,
    }
    order_time_in_force = {"entry": "gtc", "exit": "gtc"}

    # Узкий SL и трейлинг (будут переоптимизированы)
    stoploss = -0.004
    trailing_stop = True
    trailing_stop_positive = 0.003
    trailing_stop_positive_offset = 0.006
    trailing_only_offset_is_reached = True

    # -----------------
    # ПАРАМЕТРЫ (для гиперопта/тонкой настройки)
    # -----------------
    # Время торговли 07:00–20:00 UTC фиксировано фильтром времени

    # Keltner: EMA20 +/- atr_mult * ATR(14)
    atr_mult = DecimalParameter(1.0, 2.0, default=1.2, decimals=2, space="buy", optimize=True)

    # Волатильность: ATR% в диапазоне
    atr_min_pct = DecimalParameter(0.001, 0.010, default=0.0020, decimals=4, space="buy", optimize=True)
    atr_max_pct = DecimalParameter(0.005, 0.020, default=0.0120, decimals=4, space="buy", optimize=True)

    # Объём: значение >= rolling-quantile(volume, q)
    vol_q_window = IntParameter(96, 300, default=144, space="buy", optimize=True)
    vol_q_thres = DecimalParameter(0.50, 0.85, default=0.60, decimals=2, space="buy", optimize=True)

    # Protection params (для hyperopt пространства "protection")
    mdd_stop_candles = IntParameter(200, 400, default=288, space="protection", optimize=True)
    mdd_max_dd = DecimalParameter(0.010, 0.020, default=0.015, decimals=3, space="protection", optimize=True)
    lpp_lb_candles = IntParameter(5, 10, default=8, space="protection", optimize=True)
    lpp_stop_candles = IntParameter(5, 12, default=8, space="protection", optimize=True)
    lpp_required_profit = DecimalParameter(-0.001, 0.002, default=0.0, decimals=3, space="protection", optimize=True)

    def informative_pairs(self):
        return []

    @property
    def protections(self):
        # 5m: ~288 свечей = 1 день
        return [
            # Дневной стоп по счёту 1.5%, кулдаун ~до конца дня
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 288,
                "trade_limit": 1,
                "stop_duration_candles": int(self.mdd_stop_candles.value),
                "max_allowed_drawdown": float(self.mdd_max_dd.value),
            },
            # Кулдаун после убыточной сделки (на пару)
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": int(self.lpp_lb_candles.value),
                "trade_limit": 1,
                "stop_duration_candles": int(self.lpp_stop_candles.value),
                "required_profit": float(self.lpp_required_profit.value),
            },
        ]

    # -----------------
    # Индикаторы
    # -----------------
    def populate_indicators(self, df: DataFrame, metadata: Dict) -> DataFrame:
        # EMA20 (центральная линия Keltner)
        df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()

        # ATR(14)
        prev_close = df["close"].shift(1)
        tr = np.maximum(
            df["high"] - df["low"],
            np.maximum((df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()),
        )
        df["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
        df["atr_pct"] = df["atr"] / df["close"]

        # Keltner Channels
        atr_mult_val = float(self.atr_mult.value)
        df["kc_upper"] = df["ema20"] + atr_mult_val * df["atr"]
        df["kc_lower"] = df["ema20"] - atr_mult_val * df["atr"]

        # Объёмный перцентиль (rolling quantile)
        win = int(self.vol_q_window.value)
        q = float(self.vol_q_thres.value)
        # Используем min_periods=win для стабильности порога
        df["vol_q"] = df["volume"].rolling(win, min_periods=win).quantile(q)
        df["vol_ok"] = (df["volume"] >= df["vol_q"]).astype(int)

        # Фильтр времени UTC: 07:00–20:00
        hours = df["date"].dt.hour
        df["in_session"] = ((hours >= 7) & (hours <= 20)).astype(int)

        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        return df

    # -----------------
    # Входы
    # -----------------
    def populate_entry_trend(self, df: DataFrame, metadata: Dict) -> DataFrame:
        # Волатильность в заданном диапазоне
        vol_ok = (df["atr_pct"] >= float(self.atr_min_pct.value)) & (
            df["atr_pct"] <= float(self.atr_max_pct.value)
        )

        base_filters = vol_ok & (df["vol_ok"] == 1) & (df["in_session"] == 1)

        # LONG: выход ниже нижней ленты и возврат внутрь (пересечение снизу-вверх)
        long_revert = (df["close"].shift(1) < df["kc_lower"].shift(1)) & (df["close"] > df["kc_lower"])

        # SHORT: зеркально по верхней ленте (пересечение сверху-вниз)
        short_revert = (df["close"].shift(1) > df["kc_upper"].shift(1)) & (df["close"] < df["kc_upper"])

        df["enter_long"] = 0
        df.loc[base_filters & long_revert, "enter_long"] = 1

        df["enter_short"] = 0
        df.loc[base_filters & short_revert, "enter_short"] = 1
        return df

    # -----------------
    # Выходы управляются ROI/SL/Trailing — явных сигналов выхода не задаём
    # -----------------
    def populate_exit_trend(self, df: DataFrame, metadata: Dict) -> DataFrame:
        df["exit_long"] = 0
        df["exit_short"] = 0
        return df


