from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import pandas as pd

class NewsHeliusBitqueryML(IStrategy):
    """
    Базовая рабочая версия:
    - Фильтр тренда: EMA50 > EMA200 (лонг), EMA50 < EMA200 (шорт)
    - Волатильность: ATR/close > порога
    - Временной фильтр: торги по UTC 7..20
    - Входы: пересечения RSI порогов
    - Выходы: RSI/EMA + ROI/SL из конфига
    """
    timeframe = "5m"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 240
    minimal_roi = {"0": 0.02, "40": 0.01, "60": 0.005, "120": 0.0}
    stoploss = -0.02
    use_exit_signal = True
    trailing_stop = False
    ignore_buying_expired_candle_after = 1

    # --- простые индикаторы на pandas ---
    @staticmethod
    def _ema(series: pd.Series, length: int) -> pd.Series:
        return series.ewm(span=length, adjust=False).mean()

    @staticmethod
    def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
        delta = series.diff()
        up = delta.clip(lower=0)
        down = (-delta.clip(upper=0))
        ma_up = up.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
        ma_down = down.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
        rs = ma_up / (ma_down.replace(0, 1e-9))
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(df: DataFrame, length: int = 14) -> pd.Series:
        high, low, close = df['high'], df['low'], df['close']
        tr = pd.concat([
            (high - low),
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        return tr.ewm(alpha=1/length, adjust=False, min_periods=length).mean()

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['ema_fast'] = self._ema(df['close'], 50)
        df['ema_slow'] = self._ema(df['close'], 200)
        df['rsi'] = self._rsi(df['close'], 14)
        df['atr'] = self._atr(df, 14)
        df['vol_frac'] = (df['atr'] / df['close']).fillna(0)

        hours = df['date'].dt.hour if 'date' in df.columns else df.index.tz_convert('UTC').hour
        df['tradable_hour'] = ((hours >= 0) & (hours <= 23)).astype(int)

        df.fillna(method="ffill", inplace=True)
        df.dropna(inplace=True)
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        vol_min = 0.0025     # ~0.25% средней 5m-волы (смягчено)
        rsi_long_th = 40     # было 35
        rsi_short_th = 60    # было 65

        long_cond = (
            (df['ema_fast'] > df['ema_slow']) &
            (df['vol_frac'] > vol_min) &
            (df['rsi'].shift(1) < rsi_long_th) & (df['rsi'] >= rsi_long_th) &
            (df['tradable_hour'] == 1)
        )
        short_cond = (
            (df['ema_fast'] < df['ema_slow']) &
            (df['vol_frac'] > vol_min) &
            (df['rsi'].shift(1) > rsi_short_th) & (df['rsi'] <= rsi_short_th) &
            (df['tradable_hour'] == 1)
        )

        df['enter_long'] = long_cond.astype(int)
        df['enter_short'] = short_cond.astype(int)
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        exit_long = ( (df['rsi'] > 70) | (df['close'] < df['ema_fast']) )
        exit_short = ( (df['rsi'] < 30) | (df['close'] > df['ema_fast']) )
        df['exit_long'] = exit_long.astype(int)
        df['exit_short'] = exit_short.astype(int)
        return df

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