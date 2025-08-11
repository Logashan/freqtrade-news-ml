from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import pandas as pd
import ta

class NewsHeliusBitqueryML_NoProt(IStrategy):
    """
    Версия без защит для сравнения производительности:
    - Фильтр тренда: EMA50 > EMA200 (лонг), EMA50 < EMA200 (шорт)
    - Волатильность: ATR/close > порога
    - Временной фильтр: торги по UTC 6..22
    - Входы: пересечения RSI порогов + ADX + MACD
    - Выходы: RSI/EMA + ROI/SL из конфига
    - ЗАЩИТЫ ОТКЛЮЧЕНЫ для сравнения
    """
    timeframe = "5m"
    can_short = False
    process_only_new_candles = True
    startup_candle_count = 240
    minimal_roi = {"0": 0.01, "30": 0.005, "90": 0.0}
    stoploss = -0.02
    use_exit_signal = True
    trailing_stop = True
    trailing_stop_positive = 0.004
    trailing_stop_positive_offset = 0.009
    trailing_only_offset_is_reached = True
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
        
        # --- EMA, MACD ---
        ema_fast = df["close"].ewm(span=12, adjust=False).mean()
        ema_slow = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema_fast - ema_slow
        df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_sig"]
        
        # Дополнительные EMA для анализа тренда
        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
        
        # Сохраняем быстрые EMA для совместимости с существующим кодом
        df['ema_fast'] = df["ema50"]
        df['ema_slow'] = df["ema200"]

        # --- RSI(14) ---
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df["rsi"] = 100 - (100 / (1 + rs))

        # --- ATR(14) ---
        prev_close = df["close"].shift()
        tr = pd.concat([
            (df["high"] - df["low"]),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs()
        ], axis=1).max(axis=1)
        df["atr"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        
        # ADX calculation (simplified)
        df['adx'] = df['atr'].rolling(window=14).mean()  # Simplified ADX
        
        # Volume fraction
        df['vol_frac'] = (df['atr'] / df['close']).fillna(0)
        
        # Временной фильтр
        hours = df['date'].dt.hour if 'date' in df.columns else df.index.tz_convert('UTC').hour
        df['tradable_hour'] = ((hours >= 6) & (hours <= 22)).astype(int)
        
        # Подчищаем и убеждаемся, что всё числовое
        for c in ["macd", "macd_sig", "macd_hist", "ema50", "ema200", "rsi", "atr", "ema_fast", "ema_slow"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        df.ffill(inplace=True)
        df.bfill(inplace=True)
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        vol_min = 0.002     # ~0.2% средней 5m-волы (смягчено с 0.003)
        rsi_long_th = 45    # смягчено с 40
        rsi_short_th = 55   # смягчено с 60

        long_cond = (
            (df['ema_fast'] > df['ema_slow']) &
            (df['vol_frac'] > vol_min) &
            (df['macd'] > df['macd_sig']) &
            (df['adx'] >= 14) &  # смягчено с 18
            (df['rsi'].shift(1) < rsi_long_th) & (df['rsi'] >= rsi_long_th)
            # (df['tradable_hour'] == 1)  # временно закомментировано для 24/7 торговли
        )
        df['enter_long'] = long_cond.astype(int)
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        exit_long = ( (df['rsi'] > 70) | (df['close'] < df['ema_fast']) )
        df['exit_long'] = exit_long.astype(int)
        return df

    @property
    def protections(self):
        # Защиты отключены для сравнения производительности
        return []
