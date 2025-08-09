# Новый Фриг Бот - Продвинутая торговая система

Продвинутая торговая система на базе FreqTrade с интеграцией внешних API, машинного обучения и анализа новостного сентимента.

## 🚀 Особенности

### 📊 Мультисигнальная стратегия
- **Технический анализ**: RSI, MACD, Bollinger Bands, ATR
- **On-chain данные**: Helius API (Solana), Bitquery API
- **Новостной анализ**: Анализ сентимента новостей
- **Машинное обучение**: Ансамбль Random Forest + Gradient Boosting

### 🔧 Продвинутые функции
- **Фьючерсная торговля**: Поддержка кредитного плеча
- **Управление рисками**: Динамические стоп-лоссы и ROI
- **Мониторинг**: Автоматический мониторинг и алерты
- **Оптимизация**: Гипероптимизация параметров

## 📁 Структура проекта

```
Новый Фриг Бот/
├── strategies/
│   └── NewsHeliusBitqueryML.py    # Основная стратегия
├── signals/
│   ├── helius_signal.py           # Helius API интеграция
│   ├── bitquery_signal.py         # Bitquery API интеграция
│   ├── news_sentiment.py          # Анализ новостей
│   └── ml_model.py                # ML модели
├── config_backtest.json           # Конфигурация для бэктестинга
├── _newconfig.json                # Основная конфигурация
├── backtest_strategy.py           # Скрипт бэктестинга
├── bot_monitor.py                 # Мониторинг бота
├── check_setup.py                 # Проверка настроек
└── user_data/                     # Данные пользователя
    ├── backtest_results/          # Результаты бэктестинга
    ├── freqaimodels/              # ML модели
    └── data/                      # Исторические данные
```

## 🛠 Установка и настройка

### 1. Установка зависимостей

```bash
# Активируем виртуальное окружение
source freqtrade_venv/bin/activate

# Устанавливаем дополнительные зависимости
pip install textblob scikit-learn requests pandas numpy
```

### 2. Настройка API ключей

Отредактируйте `config_backtest.json` и добавьте ваши API ключи:

```json
{
  "external_apis": {
    "helius_api_key": "ваш_ключ_helius",
    "bitquery_api_key": "ваш_ключ_bitquery", 
    "news_api_key": "ваш_ключ_newsapi"
  }
}
```

### 3. Настройка биржи

Добавьте ваши ключи биржи в конфигурацию:

```json
{
  "exchange": {
    "name": "bybit",
    "key": "ваш_api_ключ",
    "secret": "ваш_secret_ключ"
  }
}
```

## 📈 Использование

### Бэктестинг стратегии

```bash
# Простой бэктестинг
python backtest_strategy.py

# Бэктестинг с параметрами
python backtest_strategy.py --timerange 20240101-20241231 --pairs BTC/USDT:USDT ETH/USDT:USDT

# Гипероптимизация
python backtest_strategy.py --hyperopt --epochs 200
```

### Запуск бота

```bash
# Запуск в режиме торговли
freqtrade trade --config _newconfig.json --strategy NewsHeliusBitqueryML

# Запуск в dry-run режиме
freqtrade trade --config config_backtest.json --strategy NewsHeliusBitqueryML
```

### Мониторинг

```bash
# Запуск мониторинга
python bot_monitor.py

# Генерация отчёта
python bot_monitor.py --report

# Мониторинг с кастомным интервалом
python bot_monitor.py --interval 30
```

## 🔍 Стратегия NewsHeliusBitqueryML

### Сигналы входа

Стратегия комбинирует несколько типов сигналов:

1. **Технические индикаторы** (30% веса):
   - RSI < 30 (перепроданность)
   - MACD пересекает сигнальную линию снизу вверх
   - Цена выше EMA 20

2. **Внешние API сигналы** (40% веса):
   - **Helius**: Крупные транзакции SOL, активность DEX
   - **Bitquery**: Inflow/outflow, активность китов

3. **Новостной сентимент** (15% веса):
   - Анализ настроений в новостях
   - Взвешивание по времени публикации

4. **Машинное обучение** (15% веса):
   - Предсказание направления цены
   - Ансамбль Random Forest + Gradient Boosting

### Сигналы выхода

- RSI > 70 (перекупленность)
- MACD пересекает сигнальную линию сверху вниз
- Достижение ROI или стоп-лосса
- ML модель предсказывает падение

### Управление рисками

- **Стоп-лосс**: -5% от цены входа
- **ROI**: 2% через 0 минут, 1% через 40 минут, 0.5% через 60 минут
- **Максимум открытых сделок**: 35
- **Кредитное плечо**: Динамическое (1-10x)

## 📊 Анализ производительности

### Метрики для оценки

- **Win Rate**: Процент прибыльных сделок
- **Profit Factor**: Отношение прибыли к убыткам
- **Sharpe Ratio**: Риск-скорректированная доходность
- **Maximum Drawdown**: Максимальная просадка
- **Total Return**: Общая доходность

### Примеры команд анализа

```bash
# Анализ результатов бэктестинга
freqtrade backtesting-analysis --config config_backtest.json

# Показать детали сделок
freqtrade backtesting-show --config config_backtest.json

# Создать графики
freqtrade plot-profit --config config_backtest.json
```

## 🔧 Настройка и оптимизация

### Параметры для оптимизации

```python
# В strategies/NewsHeliusBitqueryML.py
rsi_buy_threshold = IntParameter(20, 40, default=30, space="buy")
rsi_sell_threshold = IntParameter(60, 80, default=70, space="sell")
ml_weight = DecimalParameter(0.1, 1.0, default=0.3, space="buy")
external_signal_weight = DecimalParameter(0.1, 1.0, default=0.4, space="buy")
```

### Фильтры пар

```json
{
  "pairlists": [
    {
      "method": "VolumePairList",
      "number_assets": 20,
      "sort_key": "quoteVolume"
    },
    {
      "method": "AgeFilter",
      "min_days_listed": 30
    },
    {
      "method": "SpreadFilter",
      "max_spread_ratio": 0.005
    }
  ]
}
```

## 🚨 Мониторинг и алерты

### Автоматические алерты

- Критическая просадка > 10%
- Последовательные убытки > 5
- Низкая прибыльность < 2%
- Остановка бота

### Уведомления

- Telegram уведомления (если настроено)
- Логирование в файлы
- Email уведомления (можно добавить)

## 📚 API интеграции

### Helius API (Solana)

```python
# Анализ крупных транзакций
large_tx_signal = self._analyze_large_transactions()

# Анализ активности DEX
dex_activity_signal = self._analyze_dex_activity()

# Движения китов
whale_movement_signal = self._analyze_whale_movements()
```

### Bitquery API

```python
# Анализ inflow/outflow
inflow_outflow_signal = self._analyze_inflow_outflow(currency)

# Активность на DEX
dex_activity_signal = self._analyze_dex_activity(currency)

# Накопление китами
whale_accumulation_signal = self._analyze_whale_accumulation(currency)
```

### News API

```python
# Анализ сентимента новостей
sentiment_score = self._analyze_sentiment(news_data)

# Взвешивание по времени
weight = self.weight_recent ** i
```

## 🤖 Машинное обучение

### Особенности ML модели

- **Ансамбль**: Random Forest + Gradient Boosting
- **Признаки**: Технические индикаторы + внешние сигналы
- **Целевая переменная**: Направление цены через 5 периодов
- **Переобучение**: Каждые 24 часа

### Подготовка данных

```python
# Производные признаки
df['price_change'] = df['close'].pct_change()
df['volume_change'] = df['volume'].pct_change()
df['high_low_ratio'] = df['high'] / df['low']

# Лаговые признаки
for lag in [1, 2, 3, 5, 10]:
    df[f'price_lag_{lag}'] = df['close'].shift(lag)

# Скользящие средние
for window in [5, 10, 20]:
    df[f'sma_{window}'] = df['close'].rolling(window=window).mean()
```

## 🔒 Безопасность

### Рекомендации

1. **API ключи**: Храните в безопасном месте
2. **Dry-run**: Всегда тестируйте в dry-run режиме
3. **Лимиты**: Установите лимиты на торговлю
4. **Мониторинг**: Регулярно проверяйте логи
5. **Резервное копирование**: Делайте бэкапы конфигурации

### Переменные окружения

```bash
export FREQTRADE_API_KEY="ваш_ключ"
export FREQTRADE_SECRET="ваш_secret"
export HELIUS_API_KEY="ваш_ключ_helius"
export BITQUERY_API_KEY="ваш_ключ_bitquery"
```

## 📝 Логирование

### Уровни логирования

- **INFO**: Основная информация о работе
- **WARNING**: Предупреждения
- **ERROR**: Ошибки
- **DEBUG**: Детальная отладочная информация

### Файлы логов

- `logs/freqtrade.log` - Основные логи FreqTrade
- `logs/backtest.log` - Логи бэктестинга
- `logs/monitor.log` - Логи мониторинга

## 🆘 Устранение неполадок

### Частые проблемы

1. **Ошибка импорта модулей**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ошибка API ключей**:
   - Проверьте правильность ключей
   - Убедитесь в достаточности лимитов

3. **Ошибка базы данных**:
   ```bash
   rm user_data/tradesv3.sqlite
   ```

4. **Проблемы с памятью**:
   - Уменьшите количество пар
   - Увеличьте интервал обновления

### Поддержка

- Проверьте логи в `logs/`
- Используйте `check_setup.py` для диагностики
- Обратитесь к документации FreqTrade

## 📈 Планы развития

### Версия 2.0

- [ ] Интеграция с Discord API
- [ ] Веб-интерфейс для мониторинга
- [ ] Дополнительные ML модели (LSTM, Transformer)
- [ ] Интеграция с TradingView сигналами
- [ ] Автоматическая корректировка параметров

### Версия 3.0

- [ ] Мультибиржевая торговля
- [ ] Портфельная оптимизация
- [ ] Интеграция с DeFi протоколами
- [ ] AI-ассистент для принятия решений

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для подробностей.

## ⚠️ Отказ от ответственности

Торговля криптовалютами связана с высокими рисками. Этот бот предназначен только для образовательных целей. Авторы не несут ответственности за финансовые потери.

---

**Автор**: Trading Bot  
**Версия**: 1.0  
**Последнее обновление**: 2024