from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

class NewsHeliusBitqueryML(IStrategy):
    """
    Базовый каркас стратегии. Конфиг (ROI/stoploss/заказы) задаётся в config_*.json.
    Здесь важно только корректно грузиться и отдавать нужные колонки.
    """
    timeframe = "5m"
    process_only_new_candles = False
    use_exit_signal = True
    startup_candle_count = 200  # запас для индикаторов, можно менять позже

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        # Если будут индикаторы — добавим позже. На старте важно не падать на NaN.
        df.fillna(method="ffill", inplace=True)
        df.dropna(inplace=True)
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        # Базовые нули: сигналы добавим после бэктест-скелета
        df["enter_long"] = 0
        df["enter_short"] = 0
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df["exit_long"] = 0
        df["exit_short"] = 0
        return df