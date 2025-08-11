# Сводка изменений в стратегии NewsHeliusBitqueryML

## Последние обновления

### 2025-08-09 - Новая логика входа с switch-подходом

**Добавлено:**
- Параметр `entry_mode` с двумя режимами: "breakout" и "pullback"
- Donchian Channels (20 периодов) для breakout режима
- Switch-логика в методе `populate_entry_trend`

**Режим "breakout":**
- Вход по прорыву максимума/минимума за 20 свечей
- Подтверждение ростом/падением гистограммы MACD
- Использует существующие фильтры волатильности и тренда

**Режим "pullback":**
- Вход по откату к EMA_fast (50) в пределах ±0.2%
- Подтверждение кроссом MACD гистограммы через 0
- Дополнительный фильтр RSI > 50 для long, < 50 для short

**Технические детали:**
- Параметр оптимизируемый в гипероптимизации
- Сохранена полная совместимость с существующими параметрами
- Добавлены новые индикаторы в `populate_indicators`

**Файлы изменены:**
- `user_data/strategies/NewsHeliusBitqueryML.py` - основная стратегия
- `user_data/strategies/README_Entry_Logic.md` - документация по новой логике
- `test_new_entry_logic.py` - тест новой функциональности

---

## Предыдущие изменения

### 1. Добавлен импорт индикаторов
В начало файла `strategies/NewsHeliusBitqueryML.py` добавлен импорт:
```python
from strategies.indicators import calculate_all_indicators
```

### 2. Упрощена функция populate_indicators
Функция `populate_indicators()` была полностью переписана и теперь использует централизованный модуль индикаторов:

**Было (73 строки кода):**
- Ручной расчет EMA, MACD, RSI, ATR, ADX
- Отдельные циклы для каждого индикатора
- Много отладочного кода
- Сложная логика обработки данных

**Стало (8 строк кода):**
```python
def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
    df = calculate_all_indicators(df)
    for c in ["macd", "macd_sig", "rsi", "atr", "ema50", "ema200"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["vol_ok"] = (df["atr"] / df["close"] > 0.0015)
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    return df
```

**Добавлено приведение к числам** для критически важных колонок:
- `macd`, `macd_sig` - для MACD условий
- `rsi` - для RSI условий  
- `atr` - для расчета vol_ok
- `ema50`, `ema200` - для трендовых условий

### 3. Полностью заменены функции входов и выходов

#### populate_entry_trend (новая логика):
```python
def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
    trend_long  = df["ema50"] > df["ema200"]
    trend_short = df["ema50"] < df["ema200"]

    macd_cross_up   = (df["macd"] > df["macd_sig"]) & (df["macd"].shift(1) <= df["macd_sig"].shift(1))
    macd_cross_down = (df["macd"] < df["macd_sig"]) & (df["macd"].shift(1) >= df["macd_sig"].shift(1))

    rsi_ok_long  = df["rsi"] > 45
    rsi_ok_short = df["rsi"] < 55

    df["enter_long"]  = (trend_long  & df["vol_ok"] & macd_cross_up   & rsi_ok_long).astype(int)
    df["enter_short"] = (trend_short & df["vol_ok"] & macd_cross_down & rsi_ok_short).astype(int)
    return df
```

#### populate_exit_trend (новая логика):
```python
def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
    df["exit_long"]  = ((df["macd"] < df["macd_sig"]) | (df["rsi"] < 50)).astype(int)
    df["exit_short"] = ((df["macd"] > df["macd_sig"]) | (df["rsi"] > 50)).astype(int)
    return df
```

### 4. Включена поддержка коротких позиций
```python
can_short = True  # Было False
```

## Преимущества изменений

1. **Упрощение кода**: Функция populate_indicators стала в 9 раз короче
2. **Централизация**: Все индикаторы теперь рассчитываются в одном месте
3. **Переиспользование**: Код индикаторов можно использовать в других стратегиях
4. **Легкость поддержки**: Изменения в индикаторах автоматически применяются ко всем стратегиям
5. **Консистентность**: Все стратегии используют одинаковые алгоритмы расчета
6. **Поддержка коротких позиций**: Стратегия теперь может торговать в обе стороны
7. **Надежность типов**: Приведение к числам гарантирует корректную работу с MACD/RSI

## Что включает calculate_all_indicators

Функция `calculate_all_indicators()` из модуля `strategies.indicators` рассчитывает:

- **EMA**: ema_fast, ema_slow, ema50, ema200
- **MACD**: macd, macd_sig, macd_hist
- **RSI**: rsi (с настраиваемым периодом)
- **ATR**: atr (Average True Range)
- **ADX**: adx (упрощенная версия)
- **Volume**: vol_frac (относительный объем)

## Новая логика торговли

### Условия входа в длинную позицию:
- Тренд вверх: `ema50 > ema200`
- Объем OK: `vol_ok` (ATR/close > 0.0015)
- MACD пересекает сигнальную линию снизу вверх
- RSI > 45 (не перепродан)

### Условия входа в короткую позицию:
- Тренд вниз: `ema50 < ema200`
- Объем OK: `vol_ok`
- MACD пересекает сигнальную линию сверху вниз
- RSI < 55 (не перекуплен)

### Условия выхода:
- **Long**: MACD < сигнальной ИЛИ RSI < 50
- **Short**: MACD > сигнальной ИЛИ RSI > 50

## Совместимость

Все существующие колонки индикаторов сохраняются, поэтому остальной код стратегии продолжит работать без изменений.

## Проверка синтаксиса
✅ Файл успешно прошел проверку синтаксиса: `python3 -m py_compile strategies/NewsHeliusBitqueryML.py`

## Дата изменений
Изменения внесены: $(date)
