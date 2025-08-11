# Новая логика входа в стратегии NewsHeliusBitqueryML

## Обзор изменений

Стратегия теперь поддерживает два режима входа через параметр `entry_mode`:

### 1. Режим "breakout" (по умолчанию)
- **Вход по прорыву**: цена пробивает максимум/минимум за последние 20 свечей (Donchian Channels)
- **Подтверждение**: рост гистограммы MACD (импульс)
- **Фильтры**: 
  - Волатильность (`vol_ok`)
  - Режим тренда (`regime_long`/`regime_short`)

### 2. Режим "pullback"
- **Вход по откату**: цена возвращается к EMA_fast (50) в пределах ±0.2%
- **Подтверждение**: 
  - MACD гистограмма пересекает 0 снизу вверх (для long) или сверху вниз (для short)
  - RSI > 50 для long, RSI < 50 для short
- **Фильтры**: те же базовые фильтры

## Технические детали

### Добавленные индикаторы
- `donch_hi` - максимум high за 20 свечей
- `donch_hi` - минимум low за 20 свечей

### Параметр для оптимизации
```python
entry_mode = CategoricalParameter(["breakout", "pullback"], default="breakout", space="buy", optimize=True)
```

## Использование

### Для backtesting
```bash
freqtrade backtesting --strategy NewsHeliusBitqueryML --config config.json
```

### Для гипероптимизации
```bash
freqtrade hyperopt --strategy NewsHeliusBitqueryML --config config.json --epochs 100
```

Параметр `entry_mode` будет автоматически оптимизироваться вместе с другими параметрами.

## Логика работы

### Breakout режим
```python
if mode == "breakout":
    # Прорыв выше максимума 20 свечей + рост MACD гистограммы
    long_cond = base_long & (df["close"] > df["donch_hi"]) & macd_mom_up
    # Прорыв ниже минимума 20 свечей + падение MACD гистограммы  
    short_cond = base_short & (df["close"] < df["donch_lo"]) & macd_mom_down
```

### Pullback режим
```python
else:
    # Цена у EMA_fast ±0.2% + MACD кросс через 0 + RSI фильтр
    long_cond = base_long & near_ema_long & macd_cross_up & rsi_long_ok
    short_cond = base_short & near_ema_short & macd_cross_down & rsi_short_ok
```

## Совместимость

Все существующие параметры и функции стратегии сохранены. Новая логика полностью интегрирована в существующую структуру.
