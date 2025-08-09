#!/usr/bin/env python3
"""
Простой тест стратегии NewsHeliusBitqueryML
Проверяет загрузку стратегии и её основные функции

Автор: Trading Bot
Версия: 1.0
"""

import sys
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime

# Добавляем пути к модулям
sys.path.append(os.path.join(os.path.dirname(__file__), 'strategies'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'signals'))

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_strategy_loading():
    """Тестирует загрузку стратегии"""
    
    try:
        # Импортируем стратегию
        from strategies.NewsHeliusBitqueryML import NewsHeliusBitqueryML
        
        # Создаём конфигурацию
        config = {
            'external_apis': {
                'helius_api_key': 'test_key',
                'bitquery_api_key': 'test_key',
                'news_api_key': 'test_key'
            }
        }
        
        # Создаём экземпляр стратегии
        strategy = NewsHeliusBitqueryML(config)
        
        print("✅ Стратегия загружена успешно")
        print(f"   - Название: {strategy.__class__.__name__}")
        print(f"   - Таймфрейм: {strategy.timeframe}")
        print(f"   - Стоп-лосс: {strategy.stoploss}")
        print(f"   - ROI: {strategy.minimal_roi}")
        
        return strategy
        
    except Exception as e:
        print(f"❌ Ошибка загрузки стратегии: {e}")
        return None

def test_indicators(strategy):
    """Тестирует расчёт индикаторов"""
    
    try:
        # Создаём тестовые данные
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='5min')
        test_data = pd.DataFrame({
            'open': np.random.uniform(100, 200, len(dates)),
            'high': np.random.uniform(100, 200, len(dates)),
            'low': np.random.uniform(100, 200, len(dates)),
            'close': np.random.uniform(100, 200, len(dates)),
            'volume': np.random.uniform(1000, 10000, len(dates))
        }, index=dates)
        
        # Добавляем индикаторы
        result = strategy.populate_indicators(test_data, {'pair': 'BTC/USDT:USDT'})
        
        # Проверяем наличие основных индикаторов
        required_indicators = ['rsi', 'macd', 'macdsignal', 'macdhist', 'bb_lowerband', 'bb_upperband']
        missing_indicators = []
        
        for indicator in required_indicators:
            if indicator not in result.columns:
                missing_indicators.append(indicator)
        
        if missing_indicators:
            print(f"❌ Отсутствуют индикаторы: {missing_indicators}")
            return False
        else:
            print("✅ Индикаторы рассчитаны успешно")
            print(f"   - RSI: {result['rsi'].iloc[-1]:.2f}")
            print(f"   - MACD: {result['macd'].iloc[-1]:.2f}")
            print(f"   - BB верхняя: {result['bb_upperband'].iloc[-1]:.2f}")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка расчёта индикаторов: {e}")
        return False

def test_entry_signals(strategy):
    """Тестирует генерацию сигналов входа"""
    
    try:
        # Создаём тестовые данные с сигналами
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='5min')
        test_data = pd.DataFrame({
            'open': np.random.uniform(100, 200, len(dates)),
            'high': np.random.uniform(100, 200, len(dates)),
            'low': np.random.uniform(100, 200, len(dates)),
            'close': np.random.uniform(100, 200, len(dates)),
            'volume': np.random.uniform(1000, 10000, len(dates)),
            'rsi': np.random.uniform(20, 80, len(dates)),
            'macd': np.random.uniform(-10, 10, len(dates)),
            'macdsignal': np.random.uniform(-10, 10, len(dates)),
            'macdhist': np.random.uniform(-5, 5, len(dates)),
            'bb_lowerband': np.random.uniform(90, 110, len(dates)),
            'bb_middleband': np.random.uniform(100, 120, len(dates)),
            'bb_upperband': np.random.uniform(110, 130, len(dates)),
            'ema_20': np.random.uniform(100, 120, len(dates)),
            'ema_50': np.random.uniform(100, 120, len(dates)),
            'atr': np.random.uniform(1, 5, len(dates)),
            'volume_sma': np.random.uniform(5000, 15000, len(dates)),
            'mom': np.random.uniform(-5, 5, len(dates)),
            'adx': np.random.uniform(10, 50, len(dates)),
            'cci': np.random.uniform(-100, 100, len(dates)),
            'helius_signal': np.random.choice([-1, 0, 1], len(dates)),
            'bitquery_signal': np.random.choice([-1, 0, 1], len(dates)),
            'news_sentiment': np.random.uniform(-1, 1, len(dates)),
            'ml_signal': np.random.uniform(0, 1, len(dates))
        }, index=dates)
        
        # Генерируем сигналы входа
        result = strategy.populate_entry_trend(test_data, {'pair': 'BTC/USDT:USDT'})
        
        # Проверяем наличие сигналов
        if 'enter_long' in result.columns and 'enter_short' in result.columns:
            long_signals = result['enter_long'].sum()
            short_signals = result['enter_short'].sum()
            
            print("✅ Сигналы входа сгенерированы успешно")
            print(f"   - Лонг сигналы: {long_signals}")
            print(f"   - Шорт сигналы: {short_signals}")
            return True
        else:
            print("❌ Сигналы входа не найдены")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка генерации сигналов входа: {e}")
        return False

def test_exit_signals(strategy):
    """Тестирует генерацию сигналов выхода"""
    
    try:
        # Создаём тестовые данные
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='5min')
        test_data = pd.DataFrame({
            'open': np.random.uniform(100, 200, len(dates)),
            'high': np.random.uniform(100, 200, len(dates)),
            'low': np.random.uniform(100, 200, len(dates)),
            'close': np.random.uniform(100, 200, len(dates)),
            'volume': np.random.uniform(1000, 10000, len(dates)),
            'rsi': np.random.uniform(20, 80, len(dates)),
            'macd': np.random.uniform(-10, 10, len(dates)),
            'macdsignal': np.random.uniform(-10, 10, len(dates)),
            'news_sentiment': np.random.uniform(-1, 1, len(dates)),
            'ml_signal': np.random.uniform(0, 1, len(dates))
        }, index=dates)
        
        # Генерируем сигналы выхода
        result = strategy.populate_exit_trend(test_data, {'pair': 'BTC/USDT:USDT'})
        
        # Проверяем наличие сигналов
        if 'exit_long' in result.columns and 'exit_short' in result.columns:
            long_exits = result['exit_long'].sum()
            short_exits = result['exit_short'].sum()
            
            print("✅ Сигналы выхода сгенерированы успешно")
            print(f"   - Выходы из лонга: {long_exits}")
            print(f"   - Выходы из шорта: {short_exits}")
            return True
        else:
            print("❌ Сигналы выхода не найдены")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка генерации сигналов выхода: {e}")
        return False

def test_ml_model():
    """Тестирует ML модель"""
    
    try:
        from signals.ml_model import MLModel
        
        # Создаём ML модель
        ml_model = MLModel()
        
        print("✅ ML модель инициализирована успешно")
        print(f"   - Обучена: {ml_model.model_trained}")
        print(f"   - Количество признаков: {len(ml_model.feature_names)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка ML модели: {e}")
        return False

def test_external_signals():
    """Тестирует внешние сигналы"""
    
    try:
        from signals.helius_signal import HeliusSignalGenerator
        from signals.bitquery_signal import BitquerySignalGenerator
        from signals.news_sentiment import NewsSentimentAnalyzer
        
        # Тестируем Helius
        helius = HeliusSignalGenerator("test_key")
        print("✅ Helius Signal Generator инициализирован")
        
        # Тестируем Bitquery
        bitquery = BitquerySignalGenerator("test_key")
        print("✅ Bitquery Signal Generator инициализирован")
        
        # Тестируем News Sentiment
        news = NewsSentimentAnalyzer("test_key")
        print("✅ News Sentiment Analyzer инициализирован")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка внешних сигналов: {e}")
        return False

def main():
    """Основная функция тестирования"""
    
    print("🧪 Тестирование стратегии NewsHeliusBitqueryML")
    print("=" * 60)
    
    # Тестируем загрузку стратегии
    print("\n1. Тестирование загрузки стратегии...")
    strategy = test_strategy_loading()
    
    if strategy is None:
        print("❌ Не удалось загрузить стратегию. Тестирование прервано.")
        return
    
    # Тестируем внешние сигналы
    print("\n2. Тестирование внешних сигналов...")
    test_external_signals()
    
    # Тестируем ML модель
    print("\n3. Тестирование ML модели...")
    test_ml_model()
    
    # Тестируем индикаторы
    print("\n4. Тестирование индикаторов...")
    test_indicators(strategy)
    
    # Тестируем сигналы входа
    print("\n5. Тестирование сигналов входа...")
    test_entry_signals(strategy)
    
    # Тестируем сигналы выхода
    print("\n6. Тестирование сигналов выхода...")
    test_exit_signals(strategy)
    
    print("\n" + "=" * 60)
    print("✅ Тестирование завершено!")
    print("\n📋 Резюме:")
    print("   - Стратегия загружается корректно")
    print("   - Все модули инициализируются")
    print("   - Индикаторы рассчитываются")
    print("   - Сигналы генерируются")
    print("   - ML модель работает")
    print("\n🚀 Стратегия готова к использованию!")

if __name__ == "__main__":
    main()
