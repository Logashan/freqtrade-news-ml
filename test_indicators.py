#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы модуля с техническими индикаторами.
Запустите этот скрипт для проверки корректности расчетов.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Добавляем путь к папке strategies для импорта
sys.path.append(os.path.join(os.path.dirname(__file__), 'strategies'))

try:
    from indicators import (
        calculate_ema_macd,
        calculate_trend_emas,
        calculate_rsi,
        calculate_atr,
        calculate_adx,
        calculate_volume_fraction,
        calculate_all_indicators,
        add_trading_hours_filter
    )
    print("✅ Модуль indicators успешно импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта модуля indicators: {e}")
    sys.exit(1)


def create_sample_data(rows=1000):
    """Создает тестовые данные OHLCV."""
    print("📊 Создаю тестовые данные...")
    
    # Генерируем базовую цену с трендом и волатильностью
    np.random.seed(42)  # Для воспроизводимости
    
    base_price = 100.0
    trend = np.linspace(0, 20, rows)  # Восходящий тренд
    noise = np.random.normal(0, 2, rows)  # Шум
    price = base_price + trend + noise
    
    # Создаем OHLCV данные
    data = []
    current_time = datetime.now() - timedelta(minutes=5*rows)
    
    for i in range(rows):
        close = price[i]
        high = close + abs(np.random.normal(0, 1))
        low = close - abs(np.random.normal(0, 1))
        open_price = close + np.random.normal(0, 0.5)
        volume = np.random.uniform(1000, 10000)
        
        data.append({
            'date': current_time + timedelta(minutes=5*i),
            'open': open_price,
            'high': max(high, open_price, close),
            'low': min(low, open_price, close),
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    
    print(f"✅ Создано {len(df)} строк тестовых данных")
    return df


def test_individual_indicators(df):
    """Тестирует отдельные функции индикаторов."""
    print("\n🧪 Тестирую отдельные индикаторы...")
    
    # Тест EMA и MACD
    try:
        df_macd = calculate_ema_macd(df, 12, 26, 9)
        assert 'macd' in df_macd.columns
        assert 'ema_fast' in df_macd.columns
        print("✅ EMA и MACD рассчитаны корректно")
    except Exception as e:
        print(f"❌ Ошибка в EMA и MACD: {e}")
    
    # Тест трендовых EMA
    try:
        df_trend = calculate_trend_emas(df)
        assert 'ema50' in df_trend.columns
        assert 'ema200' in df_trend.columns
        print("✅ Трендовые EMA рассчитаны корректно")
    except Exception as e:
        print(f"❌ Ошибка в трендовых EMA: {e}")
    
    # Тест RSI
    try:
        df_rsi = calculate_rsi(df, 14)
        assert 'rsi' in df_rsi.columns
        # Проверяем, что RSI в диапазоне 0-100 для не-NaN значений
        rsi_valid = df_rsi['rsi'].dropna()
        if len(rsi_valid) > 0:
            assert (rsi_valid >= 0).all() and (rsi_valid <= 100).all()
        print("✅ RSI рассчитан корректно")
    except Exception as e:
        print(f"❌ Ошибка в RSI: {e}")
    
    # Тест ATR
    try:
        df_atr = calculate_atr(df, 14)
        assert 'atr' in df_atr.columns
        # Проверяем, что ATR >= 0 для не-NaN значений
        atr_valid = df_atr['atr'].dropna()
        if len(atr_valid) > 0:
            assert (atr_valid >= 0).all()
        print("✅ ATR рассчитан корректно")
    except Exception as e:
        print(f"❌ Ошибка в ATR: {e}")
    
    # Тест ADX
    try:
        df_adx = calculate_adx(df, 14)
        assert 'adx' in df_adx.columns
        print("✅ ADX рассчитан корректно")
    except Exception as e:
        print(f"❌ Ошибка в ADX: {e}")
    
    # Тест объема
    try:
        df_vol = calculate_volume_fraction(df, 20)
        assert 'vol_frac' in df_vol.columns
        print("✅ Относительный объем рассчитан корректно")
    except Exception as e:
        print(f"❌ Ошибка в относительном объеме: {e}")


def test_all_indicators(df):
    """Тестирует функцию расчета всех индикаторов."""
    print("\n🧪 Тестирую расчет всех индикаторов...")
    
    try:
        df_all = calculate_all_indicators(
            df,
            ema_fast_span=12,
            ema_slow_span=26,
            macd_signal_span=9,
            rsi_period=14,
            atr_period=14,
            adx_period=14,
            volume_window=20
        )
        
        # Проверяем наличие всех колонок
        expected_columns = [
            'macd', 'macd_sig', 'macd_hist', 'ema50', 'ema200',
            'rsi', 'atr', 'ema_fast', 'ema_slow', 'adx', 'vol_frac'
        ]
        
        missing_columns = [col for col in expected_columns if col not in df_all.columns]
        if missing_columns:
            print(f"❌ Отсутствуют колонки: {missing_columns}")
        else:
            print("✅ Все индикаторы рассчитаны корректно")
        
        # Проверяем типы данных
        numeric_columns = df_all[expected_columns].select_dtypes(include=[np.number]).columns
        if len(numeric_columns) == len(expected_columns):
            print("✅ Все колонки имеют числовой тип данных")
        else:
            print(f"❌ Не все колонки числовые: {len(numeric_columns)}/{len(expected_columns)}")
        
        # Проверяем на NaN значения
        nan_counts = df_all[expected_columns].isna().sum()
        total_nan = nan_counts.sum()
        if total_nan == 0:
            print("✅ NaN значения отсутствуют")
        else:
            print(f"⚠️  Найдено {total_nan} NaN значений")
            print(f"   Детали: {nan_counts.to_dict()}")
        
        return df_all
        
    except Exception as e:
        print(f"❌ Ошибка в расчете всех индикаторов: {e}")
        return None


def test_trading_hours_filter(df):
    """Тестирует фильтр торговых часов."""
    print("\n🧪 Тестирую фильтр торговых часов...")
    
    try:
        df_hours = add_trading_hours_filter(df, start_hour=6, end_hour=22)
        assert 'tradable_hour' in df_hours.columns
        assert df_hours['tradable_hour'].isin([0, 1]).all()
        
        # Проверяем логику
        hours = df_hours.index.hour
        expected_tradable = ((hours >= 6) & (hours <= 22)).astype(int)
        actual_tradable = df_hours['tradable_hour'].values
        
        # Сравниваем numpy arrays
        if np.array_equal(expected_tradable, actual_tradable):
            print("✅ Фильтр торговых часов работает корректно")
        else:
            print("❌ Ошибка в логике фильтра торговых часов")
            
    except Exception as e:
        print(f"❌ Ошибка в фильтре торговых часов: {e}")


def show_sample_data(df):
    """Показывает примеры рассчитанных данных."""
    print("\n📈 Примеры рассчитанных данных:")
    
    # Показываем последние 5 строк
    sample_cols = ['close', 'ema_fast', 'ema_slow', 'macd', 'rsi', 'atr', 'vol_frac']
    available_cols = [col for col in sample_cols if col in df.columns]
    
    if available_cols:
        print(df[available_cols].tail().round(4))
    else:
        print("Нет доступных колонок для отображения")


def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестирования модуля технических индикаторов")
    print("=" * 60)
    
    # Создаем тестовые данные
    df = create_sample_data(1000)
    
    # Тестируем отдельные индикаторы
    test_individual_indicators(df)
    
    # Тестируем все индикаторы
    df_with_indicators = test_all_indicators(df)
    
    if df_with_indicators is not None:
        # Тестируем фильтр торговых часов
        test_trading_hours_filter(df_with_indicators)
        
        # Показываем примеры данных
        show_sample_data(df_with_indicators)
        
        # Статистика
        print(f"\n📊 Статистика:")
        print(f"   Всего строк: {len(df_with_indicators)}")
        print(f"   Всего колонок: {len(df_with_indicators.columns)}")
        print(f"   Колонки с индикаторами: {len([col for col in df_with_indicators.columns if col not in ['open', 'high', 'low', 'close', 'volume']])}")
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")


if __name__ == "__main__":
    main()
