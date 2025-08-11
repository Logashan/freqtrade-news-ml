# RUNBOOK

1) Активация:
   `source freqtrade_venv/bin/activate`

2) Данные:
   `freqtrade download-data --config config_backtest.json --timeframes 15m 1h --timerange 20250610-20250809`

3) OOS-проверка:
   `freqtrade backtesting --config config_backtest.json --strategy NewsHeliusBitqueryML --strategy-path user_data/strategies --timerange 20250710-20250809 --max-open-trades 1`

Подсказки:
- Мало сделок? Чуть уменьшай Donchian/ATR/ADX.
- Много шума и PF падает? Чуть увеличивай пороги.
