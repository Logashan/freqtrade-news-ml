import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)

class TestSimple(IStrategy):
    timeframe = "5m"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 30
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    position_adjustment_enable = False
    
    minimal_roi = {
        "0": 0.01,
        "10": 0.005,
        "20": 0.0
    }
    
    stoploss = -0.02
    
    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Простые индикаторы
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        
        return df

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Простые условия входа
        long_cond = df["close"] > df["sma_20"]
        short_cond = df["close"] < df["sma_20"]
        
        df["enter_long"] = 0
        df["enter_short"] = 0
        df.loc[long_cond, "enter_long"] = 1
        df.loc[short_cond, "enter_short"] = 1
        
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Простые условия выхода
        exit_long = df["close"] < df["sma_50"]
        exit_short = df["close"] > df["sma_50"]
        
        df["exit_long"] = 0
        df["exit_short"] = 0
        df.loc[exit_long, "exit_long"] = 1
        df.loc[exit_short, "exit_short"] = 1
        
        return df
