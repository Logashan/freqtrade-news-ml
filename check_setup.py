#!/usr/bin/env python3
"""
Скрипт проверки корректности установки и настройки торгового бота
Автор: Trading Bot
Версия: 1.0
"""

import os
import sys
import json
import importlib
from pathlib import Path

def check_python_version():
    """Проверяет версию Python"""
    print("🐍 Проверка версии Python...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Требуется Python 3.11+")
        return False

def check_dependencies():
    """Проверяет установку основных зависимостей"""
    print("\n📦 Проверка зависимостей...")
    
    dependencies = {
        'freqtrade': 'Freqtrade',
        'pandas': 'Pandas',
        'numpy': 'NumPy', 
        'talib': 'TA-Lib',
        'xgboost': 'XGBoost',
        'requests': 'Requests',
        'ccxt': 'CCXT',
        'pandas_ta': 'Pandas TA'
    }
    
    all_ok = True
    
    for module, name in dependencies.items():
        try:
            importlib.import_module(module)
            print(f"   ✅ {name} - установлен")
        except ImportError:
            print(f"   ❌ {name} - НЕ установлен")
            all_ok = False
    
    return all_ok

def check_config_file():
    """Проверяет конфигурационный файл"""
    print("\n⚙️ Проверка конфигурации...")
    
    config_path = Path("config_futures.json")
    
    if not config_path.exists():
        print("   ❌ Файл config_futures.json не найден")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Проверяем ключевые параметры
        required_keys = [
            'exchange', 'pair_whitelist', 'stake_currency', 
            'dry_run', 'strategy', 'trading_mode'
        ]
        
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            print(f"   ❌ Отсутствуют ключи: {missing_keys}")
            return False
        
        print("   ✅ Структура конфигурации - OK")
        
        # Проверяем критические настройки
        if config.get('dry_run', True):
            print("   ℹ️  Режим: DRY RUN (демо торговля)")
        else:
            print("   ⚠️  Режим: LIVE TRADING (реальные сделки)")
        
        print(f"   ℹ️  Биржа: {config.get('exchange', {}).get('name', 'не указана')}")
        print(f"   ℹ️  Пар для торговли: {len(config.get('pair_whitelist', []))}")
        print(f"   ℹ️  Стратегия: {config.get('strategy', 'не указана')}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"   ❌ Ошибка парсинга JSON: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка чтения конфигурации: {e}")
        return False

def check_strategy_files():
    """Проверяет файлы стратегий"""
    print("\n📊 Проверка стратегий...")
    
    strategies_dir = Path("strategies")
    
    if not strategies_dir.exists():
        print("   ❌ Директория strategies не найдена")
        return False
    
    strategy_file = strategies_dir / "NewsHeliusBitqueryML.py"
    
    if not strategy_file.exists():
        print("   ❌ Файл стратегии NewsHeliusBitqueryML.py не найден")
        return False
    
    print("   ✅ Файл стратегии найден")
    
    # Проверяем импорт стратегии
    try:
        sys.path.insert(0, str(strategies_dir))
        import NewsHeliusBitqueryML
        print("   ✅ Стратегия успешно импортируется")
        return True
    except Exception as e:
        print(f"   ❌ Ошибка импорта стратегии: {e}")
        return False

def check_signal_modules():
    """Проверяет модули внешних сигналов"""
    print("\n📡 Проверка модулей сигналов...")
    
    signals_dir = Path("signals")
    
    if not signals_dir.exists():
        print("   ❌ Директория signals не найдена")
        return False
    
    signal_files = [
        "helius_signal.py",
        "bitquery_signal.py", 
        "news_sentiment.py"
    ]
    
    all_ok = True
    
    for file_name in signal_files:
        file_path = signals_dir / file_name
        if file_path.exists():
            print(f"   ✅ {file_name} найден")
        else:
            print(f"   ❌ {file_name} НЕ найден")
            all_ok = False
    
    # Проверяем импорты
    try:
        sys.path.insert(0, str(signals_dir))
        from helius_signal import HeliusSignalGenerator
        from bitquery_signal import BitquerySignalGenerator
        from news_sentiment import NewsSentimentAnalyzer
        print("   ✅ Все модули сигналов импортируются")
    except Exception as e:
        print(f"   ❌ Ошибка импорта модулей: {e}")
        all_ok = False
    
    return all_ok

def check_scripts():
    """Проверяет исполняемые скрипты"""
    print("\n🔧 Проверка скриптов...")
    
    scripts = {
        "install_freqtrade.sh": "Скрипт установки",
        "run_futures.sh": "Скрипт запуска"
    }
    
    all_ok = True
    
    for script_name, description in scripts.items():
        script_path = Path(script_name)
        if script_path.exists():
            if os.access(script_path, os.X_OK):
                print(f"   ✅ {description} - найден и исполняем")
            else:
                print(f"   ⚠️  {description} - найден, но не исполняем")
                print(f"      Выполните: chmod +x {script_name}")
        else:
            print(f"   ❌ {description} - НЕ найден")
            all_ok = False
    
    return all_ok

def check_directories():
    """Проверяет необходимые директории"""
    print("\n📁 Проверка директорий...")
    
    required_dirs = [
        "strategies",
        "signals", 
        "logs",
        "user_data"
    ]
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"   ✅ {dir_name}/ существует")
        else:
            print(f"   ⚠️  {dir_name}/ не существует, создаём...")
            dir_path.mkdir(exist_ok=True)
    
    return True

def main():
    """Основная функция проверки"""
    print("🔍 ПРОВЕРКА УСТАНОВКИ ТОРГОВОГО БОТА")
    print("="*50)
    
    checks = [
        ("Python версия", check_python_version),
        ("Зависимости", check_dependencies),
        ("Конфигурация", check_config_file),
        ("Стратегии", check_strategy_files),
        ("Модули сигналов", check_signal_modules),
        ("Скрипты", check_scripts),
        ("Директории", check_directories)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"   ❌ Ошибка при проверке {check_name}: {e}")
            results.append((check_name, False))
    
    # Итоговый отчёт
    print("\n" + "="*50)
    print("📋 ИТОГОВЫЙ ОТЧЁТ:")
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ ПРОЙДЕНО" if result else "❌ НЕ ПРОЙДЕНО"
        print(f"   {check_name}: {status}")
        if result:
            passed += 1
    
    print("\n" + "="*50)
    
    if passed == total:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print("   Бот готов к запуску: ./run_futures.sh")
    else:
        print(f"⚠️  ПРОЙДЕНО {passed}/{total} ПРОВЕРОК")
        print("   Исправьте ошибки перед запуском бота")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)