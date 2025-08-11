import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.strategy.parameters import CategoricalParameter
from freqtrade.persistence import Trade
from freqtrade.exchange import timeframe_to_minutes
import talib.abstract as ta
import pandas_ta as pta
from freqtrade.strategy import DecimalParameter, IntParameter, CategoricalParameter
import logging
from collections import defaultdict
import warnings
warnings.filterwarnings("ignore")
import talib as tal
import pandas_ta as pta

logger = logging.getLogger(__name__)

class NewsHeliusBitqueryML_Hyperopt(IStrategy):
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
    
    # Параметры для гипероптимизации ROI
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
        "atr_period": 14
    }
    
    sell_params = {
        "rsi_exit_long": 70,
        "ema_exit_long": True
    }
    
    # Параметры для гипероптимизации ROI
    roi_params = {
        "roi_0": 0.01,
        "roi_30": 0.005,
        "roi_90": 0.0
    }
    
    # Параметры для гипероптимизации Stoploss
    stoploss_params = {
        "stoploss": -0.02
    }
    
    # Параметры для гипероптимизации Trailing Stop
    trailing_params = {
        "trailing_stop": True,
        "trailing_stop_positive": 0.004,
        "trailing_stop_positive_offset": 0.009,
        "trailing_only_offset_is_reached": True
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        
        # --- EMA, MACD ---
        ema_fast = df["close"].ewm(span=self.buy_params['ema_fast'], adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.buy_params['ema_slow'], adjust=False).mean()
        df["macd"] = ema_fast - ema_slow
        df["macd_sig"] = df["macd"].ewm(span=self.buy_params['macd_signal'], adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_sig"]
        
        # Дополнительные EMA для анализа тренда
        df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
        
        # Сохраняем быстрые EMA для совместимости с существующим кодом
        df['ema_fast'] = ema_fast
        df['ema_slow'] = ema_slow

        # --- RSI(14) ---
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/self.buy_params['rsi_period'], min_periods=self.buy_params['rsi_period'], adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/self.buy_params['rsi_period'], min_periods=self.buy_params['rsi_period'], adjust=False).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df["rsi"] = 100 - (100 / (1 + rs))

        # --- ATR(14) ---
        prev_close = df["close"].shift()
        tr = pd.concat([
            (df["high"] - df["low"]),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs()
        ], axis=1).max(axis=1)
        df["atr"] = tr.ewm(alpha=1/self.buy_params['atr_period'], min_periods=self.buy_params['atr_period'], adjust=False).mean()
        
        # ADX calculation (simplified)
        df['adx'] = df['atr'].rolling(window=14).mean()  # Simplified ADX
        
        # Volume fraction
        df['vol_frac'] = df['volume'] / df['volume'].rolling(window=20).mean()
        
        # Подчищаем и убеждаемся, что всё числовое
        for c in ["macd", "macd_sig", "macd_hist", "ema50", "ema200", "rsi", "atr", "ema_fast", "ema_slow"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        df.ffill(inplace=True)
        df.bfill(inplace=True)
        
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        
        vol_min = self.buy_params['vol_min']
        rsi_long_th = self.buy_params['rsi_long_th']
        adx_min = self.buy_params['adx_min']
        
        long_cond = (
            (df['ema_fast'] > df['ema_slow']) &
            (df['vol_frac'] > vol_min) &
            (df['macd'] > df['macd_sig']) &
            (df['adx'] >= adx_min) &
            (df['rsi'].shift(1) < rsi_long_th) & (df['rsi'] >= rsi_long_th)
        )
        
        df['enter_long'] = long_cond.astype(int)
        
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        
        rsi_exit_long = self.sell_params['rsi_exit_long']
        ema_exit_long = self.sell_params['ema_exit_long']
        
        exit_long = (
            (df['rsi'] > rsi_exit_long) | 
            (ema_exit_long and df['close'] < df['ema_fast'])
        )
        
        df['exit_long'] = exit_long.astype(int)
        
        return df
    
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
