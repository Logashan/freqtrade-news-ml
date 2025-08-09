from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import pandas as pd
import numpy as np

class NewsHeliusBitqueryML(IStrategy):
    """
    Базовая рабочая стратегия:
      - Лонги по тренду (EMA50 > EMA200) + импульс (RSI > 55)
      - Фильтр волатильности (ATR% > 0.25)
      - Выход: ослабление импульса (RSI < 45) или слом тренда (EMA50 < EMA200)
    Примечание: шорты отключены на первом этапе.
    """
    timeframe = "5m"
    can_short = False
    process_only_new_candles = False
    use_exit_signal = True
    startup_candle_count = 200  # нужно для EMA200/ATR

    # --- индикаторы ---

    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        up = np.where(delta > 0, delta, 0.0)
        down = np.where(delta < 0, -delta, 0.0)
        roll_up = pd.Series(up, index=series.index).ewm(alpha=1/period, adjust=False).mean()
        roll_down = pd.Series(down, index=series.index).ewm(alpha=1/period, adjust=False).mean()
        rs = roll_up / (roll_down.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)  # нейтраль для первых баров

    @staticmethod
    def _atr(df: DataFrame, period: int = 14) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        return atr

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        # EMA тренд
        df["ema_fast"] = self._ema(df["close"], 50)
        df["ema_slow"] = self._ema(df["close"], 200)

        # RSI импульс
        df["rsi"] = self._rsi(df["close"], 14)

        # ATR волатильность и относительная волатильность
        df["atr"] = self._atr(df, 14)
        df["atr_pct"] = (df["atr"] / df["close"]) * 100

        # Фильтр объёма (опционально): текущий > средний за 20
        df["vol_ma20"] = df["volume"].rolling(20).mean()
        df["vol_ok"] = (df["volume"] > df["vol_ma20"]).astype(int)

        # Чистим начальные NaN
        df.fillna(method="ffill", inplace=True)
        df.dropna(inplace=True)
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        trend_up = df["ema_fast"] > df["ema_slow"]
        momentum_ok = df["rsi"] > 55
        vola_ok = df["atr_pct"] > 0.25
        vol_ok = df["vol_ok"] == 1

        # Базовый лонг-сигнал
        df["enter_long"] = (trend_up & momentum_ok & vola_ok & vol_ok).astype(int)

        # Шорты отключены
        df["enter_short"] = 0
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        exit_momentum_weak = df["rsi"] < 45
        exit_trend_break = df["ema_fast"] < df["ema_slow"]

        df["exit_long"] = (exit_momentum_weak | exit_trend_break).astype(int)
        df["exit_short"] = 0
        return df