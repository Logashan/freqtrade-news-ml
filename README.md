# freqtrade-news-ml (preset C1g)

Бот на Freqtrade со стратегией **NewsHeliusBitqueryML**.
Активный пресет: **C1g** (зафиксирован в `user_data/strategies/NewsHeliusBitqueryML.json`).

Быстрый запуск:
1) `source freqtrade_venv/bin/activate`
2) `freqtrade download-data --config config_backtest.json --timeframes 15m 1h --timerange 20250610-20250809`
3) IS: `freqtrade backtesting --config config_backtest.json --strategy NewsHeliusBitqueryML --strategy-path user_data/strategies --timerange 20250610-20250709 --max-open-trades 1`
4) OOS: `freqtrade backtesting --config config_backtest.json --strategy NewsHeliusBitqueryML --strategy-path user_data/strategies --timerange 20250710-20250809 --max-open-trades 1`
