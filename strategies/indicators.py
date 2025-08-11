"""
Модуль с улучшенными техническими индикаторами для FreqTrade стратегий.
Все индикаторы оптимизированы для производительности и точности.
"""

import pandas as pd
import numpy as np
from pandas import DataFrame


def calculate_ema_macd(df: DataFrame, ema_fast_span: int = 12, ema_slow_span: int = 26, macd_signal_span: int = 9) -> DataFrame:
    """
    Рассчитывает EMA и MACD индикаторы.
    
    Args:
        df: DataFrame с данными OHLCV
        ema_fast_span: Период быстрой EMA
        ema_slow_span: Период медленной EMA
        macd_signal_span: Период сигнальной линии MACD
    
    Returns:
        DataFrame с добавленными колонками: ema_fast, ema_slow, macd, macd_sig, macd_hist
    """
    df = df.copy()
    
    # EMA
    ema_fast = df["close"].ewm(span=ema_fast_span, adjust=False).mean()
    ema_slow = df["close"].ewm(span=ema_slow_span, adjust=False).mean()
    
    # MACD
    df["macd"] = ema_fast - ema_slow
    df["macd_sig"] = df["macd"].ewm(span=macd_signal_span, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    
    # Сохраняем EMA
    df['ema_fast'] = ema_fast
    df['ema_slow'] = ema_slow
    
    return df


def calculate_trend_emas(df: DataFrame) -> DataFrame:
    """
    Рассчитывает дополнительные EMA для анализа тренда.
    
    Args:
        df: DataFrame с данными OHLCV
    
    Returns:
        DataFrame с добавленными колонками: ema50, ema200
    """
    df = df.copy()
    
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    
    return df


def calculate_rsi(df: DataFrame, period: int = 14) -> DataFrame:
    """
    Рассчитывает RSI индикатор с использованием экспоненциального скользящего среднего.
    
    Args:
        df: DataFrame с данными OHLCV
        period: Период RSI
    
    Returns:
        DataFrame с добавленной колонкой: rsi
    """
    df = df.copy()
    
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["rsi"] = 100 - (100 / (1 + rs))
    
    return df


def calculate_atr(df: DataFrame, period: int = 14) -> DataFrame:
    """
    Рассчитывает ATR (Average True Range) индикатор.
    
    Args:
        df: DataFrame с данными OHLCV
        period: Период ATR
    
    Returns:
        DataFrame с добавленной колонкой: atr
    """
    df = df.copy()
    
    prev_close = df["close"].shift()
    tr = pd.concat([
        (df["high"] - df["low"]),
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    return df


def calculate_adx(df: DataFrame, period: int = 14) -> DataFrame:
    """
    Рассчитывает упрощенный ADX индикатор на основе ATR.
    
    Args:
        df: DataFrame с данными OHLCV
        period: Период ADX
    
    Returns:
        DataFrame с добавленной колонкой: adx
    """
    df = df.copy()
    
    # Упрощенный ADX на основе ATR
    if 'atr' not in df.columns:
        df = calculate_atr(df, period)
    
    df['adx'] = df['atr'].rolling(window=period).mean()
    
    return df


def calculate_volume_fraction(df: DataFrame, window: int = 20) -> DataFrame:
    """
    Рассчитывает относительный объем.
    
    Args:
        df: DataFrame с данными OHLCV
        window: Окно для расчета среднего объема
    
    Returns:
        DataFrame с добавленной колонкой: vol_frac
    """
    df = df.copy()
    
    df['vol_frac'] = df['volume'] / df['volume'].rolling(window=window).mean()
    
    return df


def calculate_all_indicators(df: DataFrame, 
                           ema_fast_span: int = 12, 
                           ema_slow_span: int = 26, 
                           macd_signal_span: int = 9,
                           rsi_period: int = 14,
                           atr_period: int = 14,
                           adx_period: int = 14,
                           volume_window: int = 20) -> DataFrame:
    """
    Рассчитывает все основные технические индикаторы.
    
    Args:
        df: DataFrame с данными OHLCV
        ema_fast_span: Период быстрой EMA
        ema_slow_span: Период медленной EMA
        macd_signal_span: Период сигнальной линии MACD
        rsi_period: Период RSI
        atr_period: Период ATR
        adx_period: Период ADX
        volume_window: Окно для расчета относительного объема
    
    Returns:
        DataFrame со всеми рассчитанными индикаторами
    """
    df = df.copy()
    
    # Рассчитываем все индикаторы
    df = calculate_ema_macd(df, ema_fast_span, ema_slow_span, macd_signal_span)
    df = calculate_trend_emas(df)
    df = calculate_rsi(df, rsi_period)
    df = calculate_atr(df, atr_period)
    df = calculate_adx(df, adx_period)
    df = calculate_volume_fraction(df, volume_window)
    
    # Подчищаем и убеждаемся, что всё числовое
    indicator_columns = ["macd", "macd_sig", "macd_hist", "ema50", "ema200", 
                        "rsi", "atr", "ema_fast", "ema_slow", "adx", "vol_frac"]
    
    for col in indicator_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Заполняем пропущенные значения
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    
    return df


def add_trading_hours_filter(df: DataFrame, start_hour: int = 6, end_hour: int = 22) -> DataFrame:
    """
    Добавляет фильтр торговых часов.
    
    Args:
        df: DataFrame с данными OHLCV
        start_hour: Начальный час торгов (UTC)
        end_hour: Конечный час торгов (UTC)
    
    Returns:
        DataFrame с добавленной колонкой: tradable_hour
    """
    df = df.copy()
    
    # Определяем час для каждой свечи
    if 'date' in df.columns:
        hours = df['date'].dt.hour
    else:
        # Используем индекс как datetime
        try:
            if isinstance(df.index, pd.DatetimeIndex):
                hours = df.index.hour
            else:
                # Если индекс не datetime, создаем временную метку
                hours = pd.Series([pd.Timestamp.now().hour] * len(df), index=df.index)
        except:
            # Если не получается, используем текущее время
            hours = pd.Series([pd.Timestamp.now().hour] * len(df), index=df.index)
    
    # Создаем булев массив и конвертируем в int
    tradable_condition = (hours >= start_hour) & (hours <= end_hour)
    df['tradable_hour'] = tradable_condition.astype(int)
    
    return df
