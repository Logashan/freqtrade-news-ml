# Модуль оптимизированных технических индикаторов

Этот модуль (`indicators.py`) содержит оптимизированные функции для расчета технических индикаторов, которые можно использовать в стратегиях FreqTrade.

## Особенности

- **Оптимизированные вычисления**: Использует pandas для эффективных вычислений
- **Точность**: Правильная реализация формул индикаторов
- **Переиспользование**: Модульная структура для легкого использования в разных стратегиях
- **Обработка ошибок**: Автоматическая очистка данных и заполнение пропусков

## Доступные индикаторы

### 1. EMA и MACD
```python
from .indicators import calculate_ema_macd

df = calculate_ema_macd(df, ema_fast_span=12, ema_slow_span=26, macd_signal_span=9)
# Добавляет: ema_fast, ema_slow, macd, macd_sig, macd_hist
```

### 2. Трендовые EMA
```python
from .indicators import calculate_trend_emas

df = calculate_trend_emas(df)
# Добавляет: ema50, ema200
```

### 3. RSI
```python
from .indicators import calculate_rsi

df = calculate_rsi(df, period=14)
# Добавляет: rsi
```

### 4. ATR (Average True Range)
```python
from .indicators import calculate_atr

df = calculate_atr(df, period=14)
# Добавляет: atr
```

### 5. ADX (упрощенный)
```python
from .indicators import calculate_adx

df = calculate_adx(df, period=14)
# Добавляет: adx
```

### 6. Относительный объем
```python
from .indicators import calculate_volume_fraction

df = calculate_volume_fraction(df, window=20)
# Добавляет: vol_frac
```

### 7. Все индикаторы сразу
```python
from .indicators import calculate_all_indicators

df = calculate_all_indicators(
    df,
    ema_fast_span=12,
    ema_slow_span=26,
    macd_signal_span=9,
    rsi_period=14,
    atr_period=14,
    adx_period=14,
    volume_window=20
)
# Добавляет все индикаторы: ema_fast, ema_slow, macd, macd_sig, macd_hist, 
# ema50, ema200, rsi, atr, adx, vol_frac
```

### 8. Фильтр торговых часов
```python
from .indicators import add_trading_hours_filter

df = add_trading_hours_filter(df, start_hour=6, end_hour=22)
# Добавляет: tradable_hour (1 для торговых часов, 0 для неторговых)
```

## Пример использования в стратегии

```python
from .indicators import calculate_all_indicators, add_trading_hours_filter

class MyStrategy(IStrategy):
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        
        # Рассчитываем все индикаторы
        df = calculate_all_indicators(
            df,
            ema_fast_span=12,
            ema_slow_span=26,
            macd_signal_span=9,
            rsi_period=14,
            atr_period=14,
            adx_period=14,
            volume_window=20
        )
        
        # Добавляем фильтр торговых часов
        df = add_trading_hours_filter(df, start_hour=6, end_hour=22)
        
        return df
```

## Преимущества перед стандартными библиотеками

### 1. Производительность
- Использует pandas `ewm()` вместо `rolling()` для EMA
- Оптимизированные вычисления True Range для ATR
- Эффективная обработка больших объемов данных

### 2. Точность
- Правильная реализация формулы RSI с экспоненциальным скользящим средним
- Корректный расчет True Range для ATR
- Точные вычисления MACD

### 3. Надежность
- Автоматическая очистка данных (`pd.to_numeric`)
- Заполнение пропущенных значений (`ffill`, `bfill`)
- Обработка ошибок деления на ноль

### 4. Гибкость
- Настраиваемые периоды для всех индикаторов
- Модульная структура для выборочного использования
- Легкая интеграция в существующие стратегии

## Сравнение с talib

| Аспект | Наш модуль | talib |
|--------|------------|-------|
| Производительность | Высокая (pandas) | Очень высокая (C) |
| Точность | Высокая | Высокая |
| Зависимости | Только pandas | C библиотека + обертки |
| Настраиваемость | Высокая | Средняя |
| Отладка | Легкая | Сложная |
| Кроссплатформенность | 100% | Зависит от компиляции |

## Рекомендации по использованию

1. **Для новых стратегий**: Используйте `calculate_all_indicators()` для быстрого старта
2. **Для оптимизации**: Используйте отдельные функции для выборочного расчета
3. **Для отладки**: Включите логирование в стратегии для мониторинга качества данных
4. **Для гипероптимизации**: Используйте параметры стратегии для настройки периодов индикаторов

## Обновление существующих стратегий

Если у вас есть существующие стратегии, вы можете легко обновить их:

1. Замените вызовы `ta.EMA()`, `ta.RSI()`, `ta.MACD()` на функции из нашего модуля
2. Обновите метод `populate_indicators()`
3. Убедитесь, что все необходимые колонки доступны в `populate_entry_trend()` и `populate_exit_trend()`

## Поддержка

При возникновении проблем:
1. Проверьте логи на наличие ошибок
2. Убедитесь, что все необходимые колонки присутствуют в DataFrame
3. Проверьте типы данных (должны быть числовыми)
4. Убедитесь, что нет деления на ноль в расчетах
