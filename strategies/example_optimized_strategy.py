"""
Пример стратегии с использованием оптимизированных технических индикаторов.
Эта стратегия демонстрирует, как использовать новый модуль indicators.py
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_minutes
import warnings
warnings.filterwarnings("ignore")

# Импортируем наш модуль с индикаторами
from .indicators import calculate_all_indicators, add_trading_hours_filter

logger = logging.getLogger(__name__)


class OptimizedIndicatorsStrategy(IStrategy):
    """
    Стратегия с использованием оптимизированных технических индикаторов.
    
    Особенности:
    - Использует модуль indicators.py для расчета индикаторов
    - Оптимизированные вычисления EMA, MACD, RSI, ATR
    - Дополнительные EMA50 и EMA200 для анализа тренда
    - Фильтр торговых часов
    - Настраиваемые параметры для гипероптимизации
    """
    
    timeframe = "5m"
    can_short = False
    process_only_new_candles = True
    startup_candle_count = 240
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
    
    # ROI настраивается через гипероптимизацию
    minimal_roi = {
        "0": 0.01,
        "30": 0.005,
        "90": 0.0
    }
    
    stoploss = -0.02
    
    trailing_stop = True
    trailing_stop_positive = 0.004
    trailing_stop_positive_offset = 0.009
    trailing_only_offset_is_reached = True
    
    ignore_buying_expired_candle_after = 1
    
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
        "atr_period": 14,
        "volume_window": 20
    }
    
    sell_params = {
        "rsi_exit_long": 70,
        "ema_exit_long": True
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Рассчитывает все технические индикаторы используя оптимизированный модуль.
        """
        df = dataframe.copy()
        
        # Используем функцию из модуля indicators.py для расчета всех индикаторов
        df = calculate_all_indicators(
            df,
            ema_fast_span=self.buy_params['ema_fast'],
            ema_slow_span=self.buy_params['ema_slow'],
            macd_signal_span=self.buy_params['macd_signal'],
            rsi_period=self.buy_params['rsi_period'],
            atr_period=self.buy_params['atr_period'],
            adx_period=14,
            volume_window=self.buy_params['volume_window']
        )
        
        # Добавляем фильтр торговых часов
        df = add_trading_hours_filter(df, start_hour=6, end_hour=22)
        
        # Логируем статистику по индикаторам для отладки
        try:
            logger.info(f"[DBG] Indicators calculated successfully for {metadata['pair']}")
            logger.info(f"[DBG] Columns: {list(df.columns)}")
            logger.info(f"[DBG] Data shape: {df.shape}")
            
            # Проверяем наличие NaN значений
            nan_counts = {}
            for col in ['ema_fast', 'ema_slow', 'ema50', 'ema200', 'rsi', 'macd', 'macd_sig', 'atr', 'adx', 'vol_frac']:
                if col in df.columns:
                    nan_counts[col] = df[col].isna().sum()
            
            logger.info(f"[DBG] NaN counts: {nan_counts}")
            
        except Exception as e:
            logger.warning(f"[DBG] Error in indicators debug: {e}")
        
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Определяет условия для входа в позицию.
        """
        df = dataframe.copy()
        
        vol_min = self.buy_params['vol_min']
        rsi_long_th = self.buy_params['rsi_long_th']
        adx_min = self.buy_params['adx_min']
        
        # Условия для входа в лонг позицию
        ema_trend_cond = (df['ema50'] > df['ema200'])  # Тренд вверх
        ema_fast_cond = (df['ema_fast'] > df['ema_slow'])  # Быстрая EMA выше медленной
        vol_cond = (df['vol_frac'] > vol_min)  # Объем выше среднего
        macd_cond = (df['macd'] > df['macd_sig'])  # MACD выше сигнальной линии
        adx_cond = (df['adx'] >= adx_min)  # ADX выше минимального порога
        rsi_cond = (df['rsi'].shift(1) < rsi_long_th) & (df['rsi'] >= rsi_long_th)  # RSI пересекает порог снизу вверх
        trading_hours_cond = (df['tradable_hour'] == 1)  # Торговые часы
        
        # Комбинируем все условия
        long_cond = (
            ema_trend_cond &
            ema_fast_cond &
            vol_cond &
            macd_cond &
            adx_cond &
            rsi_cond &
            trading_hours_cond
        )
        
        df['enter_long'] = long_cond.astype(int)
        
        # Логируем количество сигналов для отладки
        signal_count = long_cond.sum()
        if signal_count > 0:
            logger.info(f"[SIGNAL] Found {signal_count} long entry signals for {metadata['pair']}")
        
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Определяет условия для выхода из позиции.
        """
        df = dataframe.copy()
        
        rsi_exit_long = self.sell_params['rsi_exit_long']
        ema_exit_long = self.sell_params['ema_exit_long']
        
        # Условия для выхода из лонг позиции
        rsi_exit_cond = (df['rsi'] > rsi_exit_long)  # RSI выше верхнего порога
        ema_exit_cond = ema_exit_long and (df['close'] < df['ema_fast'])  # Цена ниже быстрой EMA
        
        # Комбинируем условия выхода
        exit_long = rsi_exit_cond | ema_exit_cond
        
        df['exit_long'] = exit_long.astype(int)
        
        # Логируем количество сигналов выхода для отладки
        exit_count = exit_long.sum()
        if exit_count > 0:
            logger.info(f"[SIGNAL] Found {exit_count} long exit signals for {metadata['pair']}")
        
        return df

    def custom_roi(self, dataframe: DataFrame, trade: Trade, current_time: datetime, **kwargs) -> float:
        """
        Динамический ROI на основе времени удержания позиции.
        """
        open_minutes = (current_time - trade.open_date_utc).total_seconds() / 60
        
        if open_minutes <= 30:
            return self.minimal_roi["0"]
        elif open_minutes <= 90:
            return self.minimal_roi["30"]
        else:
            return self.minimal_roi["90"]

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime, 
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Динамический стоп-лосс.
        """
        return self.stoploss

    def custom_trailing_stop(self, pair: str, trade: Trade, current_time: datetime, 
                           current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Динамический трейлинг-стоп.
        """
        if not self.trailing_stop:
            return 0
        
        if current_profit > self.trailing_stop_positive_offset:
            return self.trailing_stop_positive
        
        return 0

    @property
    def protections(self):
        """
        Защитные механизмы стратегии.
        """
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 5},
            {"method": "StoplossGuard", "lookback_period_candles": 288,
             "stop_duration_candles": 30, "only_per_pair": False, "trade_limit": 2},
            {"method": "MaxDrawdown", "lookback_period_candles": 288,
             "stop_duration_candles": 60, "max_allowed_drawdown": 8,
             "only_per_pair": False}
        ]
