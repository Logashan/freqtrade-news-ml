# REGISTRY — Новый Фриг Бот (источник истины)

_Обновлено: 2025-08-09_

### Сессия 2025-08-09 (UTC) — Чистый старт
- Цель спринта: стабилизировать стратегию и поднять PF ≥ 1.05 при MaxDD ≤ 12%.
- Линейка окон: 01-R, 02-B, 03-D, 04-T, 05-B++, 06-T2.
- Артефакты прошлых сессий сохранены, старые окна закрыты.
- Следующий шаг: 02-B — быстрая проверка стратегии и конфига.

## Сегодня (UTC) — Стабилизация ядра

- **Data OK**: 5m futures BTC/ETH/SOL ~34.7k свечей/пара, 2025-04-11 → 2025-08-09.
- **Проверка feather**: rows=34745 (spot), rows=34835 (futures).
- **Переходим к**: protections в стратегии и бэктесту с --enable-protections.

### Данные (D)
- **Пары**: BTC/USDT:USDT, ETH/USDT:USDT, SOL/USDT:USDT
- **Целевой диапазон**: ~2025-04-11 → 2025-08-09, 5m

## 1) Состояние проекта
**DONE**
- `config_futures.json` — приведён к формату Freqtrade 2025.6 (stake_amount, leverage, order_types).
- `start_bot.sh` — есть интерактивный запуск режимов.
- `backtest_strategy.py` — есть базовый скрипт запуска бэктеста через Python API.
- Dry-run запускался и доходил до загрузки конфигов/паров.

**IN PROGRESS**
- `strategies/NewsHeliusBitqueryML.py` — исправление имени класса/импортов, устранение NaN и синтакс-ошибок.
- `config_backtest.json` — минимальный конфиг на 3 пары (5m), валидация `jq`.
- Исторические данные Bybit (5m, ~120 дней) — скачивание/проверка.

**TODO (ближайшие)**
- `quick_test.py` — smoke-тест StrategyResolver (загрузка класса без запуска бота).
- `backtesting` — прогон + экспорт `backtest_trades.csv` и первичные метрики.
- Причесать `start_bot.sh`: Dry-run/Live → `config_futures.json`, Backtesting → `config_backtest.json`.
- `prediction_mode.py` — советник без ордеров (логирование рекомендаций).
- `analytics_dashboard.py` (Streamlit) — RSI/MACD/сентимент + кнопка e-mail отчёта.
- `schedule_reports.sh` + `signals/email_notify.py` — ежедневные отчёты.
- `.env` — вынести ключи (BYBIT_API_KEY/SECRET и внешние API).

---

## 2) Инвентаризация (факт наличия)
- `strategies/NewsHeliusBitqueryML.py` — [x] есть, требует фикса класса/импортов.
- `config_futures.json` — [x] валидный JSON (формат 2025.6).
- `config_backtest.json` — [x] существует, но стандартизировать до минимального (3 пары, 5m).
- `start_bot.sh` — [x] есть; **заметка**: Dry-run сейчас может использовать `config_backtest.json` → нужно переключить на `config_futures.json`.
- `signals/helius_signal.py` — [x] есть.
- `signals/bitquery_signal.py` — [x] есть.

---

## 3) Роли окон Cursor (фиксируем дисциплину)
- **R — Registry:** только статус/план/итоги (этот файл).
- **B — Build:** только правки кода/конфигов (атомарные задачи).
- **T — Test/Run:** только команды и логи (download-data, backtesting, trade).

---

## 4) Спринт «Стабилизация ядра» (сегодня)
1. **[B] Стратегия:** привести `NewsHeliusBitqueryML` к рабочему минимуму:  
   класс ровно `NewsHeliusBitqueryML(IStrategy)`, импорты минимальные, `populate_*` с `ffill`/`dropna`, сигнальные колонки = 0.
2. **[B] Конфиг бэктеста:** создать/упростить `config_backtest.json` (3 пары: BTC/ETH/SOL, 5m; формат 2025.6; `jq` ок).
3. **[T] Smoke-тест:** `quick_test.py` → «Стратегия загружена успешно».
4. **[T] Данные:** `download-data` (Bybit, 5m, 120 дней) без ошибок.
5. **[T] Backtesting:** прогнать; сохранить `backtest_trades.csv`; выписать PnL, Winrate, Avg trade, Max DD.
6. **[R] Итоги:** внести результаты и заметки (что улучшать в стратегии).

**Что именно "что улучшать в стратегии":**
- условия входа/выхода (логика `enter_*` / `exit_*`);
- фильтры волатильности и объёма;
- риск-параметры (stoploss, ROI, trailing);
- очистка данных и обработка NaN;
- проверка совместимости с Freqtrade 2025.6 (конфиг/импорты/класс).

---

## 5) T — Базовый бэктест: запланировано

### Цель
Провести базовый бэктест стратегии `NewsHeliusBitqueryML` на исторических данных Bybit (BTC/ETH/SOL, 5m, ~120 дней) для оценки базовой работоспособности.

### План выполнения
1. **Подготовка данных**
   - Скачать исторические данные: `freqtrade download-data --exchange bybit --pairs BTC/USDT:USDT ETH/USDT:USDT SOL/USDT:USDT --timeframe 5m --days 120`
   - Проверить качество данных: отсутствие NaN, корректные временные метки

2. **Запуск бэктеста**
   - Использовать `config_backtest.json` с минимальными настройками
   - Команда: `freqtrade backtesting --config config_backtest.json --strategy NewsHeliusBitqueryML`
   - Включить protections: `--enable-protections`

3. **Анализ результатов**
   - Основные метрики: Total Return, Win Rate, Profit Factor, Max Drawdown
   - Экспорт сделок: `backtest_trades.csv`
   - Графики: equity curve, drawdown, trade distribution

### Ожидаемые результаты
- Стратегия должна загружаться без ошибок
- Бэктест должен завершаться успешно
- Базовые метрики для оценки направления развития

### Критерии успеха
- [ ] Бэктест завершается без критических ошибок
- [ ] Получены базовые метрики производительности
- [ ] Экспортированы данные сделок для дальнейшего анализа
