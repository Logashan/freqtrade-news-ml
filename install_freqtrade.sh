#!/bin/bash

# Скрипт установки Freqtrade для торгового бота
# Совместимость: macOS (M-чип, ARM64)
# Версия: Freqtrade stable branch

echo "🚀 Начинаем установку Freqtrade для торгового бота..."

# Проверяем наличие brew (для установки TA-Lib)
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew не найден. Установите Homebrew сначала: https://brew.sh"
    exit 1
fi

# Проверяем наличие git
if ! command -v git &> /dev/null; then
    echo "❌ Git не найден. Установите git."
    exit 1
fi

# Проверяем Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "⚠️  Python 3.11 не найден. Устанавливаем через brew..."
    brew install python@3.11
fi

# Устанавливаем TA-Lib для macOS ARM64
echo "📦 Устанавливаем TA-Lib через Homebrew..."
brew install ta-lib

# Создаём директорию проекта если её нет
PROJECT_DIR="$(pwd)"
echo "📁 Рабочая директория: $PROJECT_DIR"

# Клонируем Freqtrade (stable branch)
if [ ! -d "freqtrade" ]; then
    echo "📥 Клонируем Freqtrade (stable branch)..."
    git clone -b stable https://github.com/freqtrade/freqtrade.git
else
    echo "📁 Freqtrade уже существует, обновляем..."
    cd freqtrade
    git pull origin stable
    cd ..
fi

# Создаём виртуальное окружение Python 3.11
echo "🐍 Создаём виртуальное окружение Python 3.11..."
python3.11 -m venv freqtrade_venv

# Активируем виртуальное окружение
echo "⚡ Активируем виртуальное окружение..."
source freqtrade_venv/bin/activate

# Обновляем pip
echo "🔄 Обновляем pip..."
pip install --upgrade pip setuptools wheel

# Устанавливаем основные зависимости
echo "📦 Устанавливаем основные зависимости..."

# Устанавливаем freqtrade с поддержкой Telegram
pip install -e freqtrade/[telegram]

# Устанавливаем дополнительные библиотеки для анализа и ML
echo "🤖 Устанавливаем библиотеки для технического анализа и ML..."
pip install pandas-ta
pip install ccxt
pip install xgboost

# Устанавливаем TA-Lib для Python (после установки системной версии)
echo "📈 Устанавливаем TA-Lib для Python..."
pip install TA-Lib

# Устанавливаем дополнительные зависимости для работы с API
echo "🌐 Устанавливаем зависимости для API..."
pip install requests
pip install python-dotenv
pip install textblob  # Для анализа сентимента
pip install vaderSentiment  # Альтернативный анализатор сентимента

# Создаём необходимые директории
echo "📂 Создаём структуру проекта..."
mkdir -p strategies
mkdir -p signals
mkdir -p logs
mkdir -p user_data/data
mkdir -p user_data/logs
mkdir -p user_data/backtest_results

# Устанавливаем права выполнения для скриптов
chmod +x *.sh

# Проверяем установку
echo "🔍 Проверяем установку..."
python -c "import freqtrade; print(f'✅ Freqtrade версия: {freqtrade.__version__}')"
python -c "import pandas_ta; print('✅ pandas-ta установлен')"
python -c "import ccxt; print('✅ ccxt установлен')" 
python -c "import xgboost; print('✅ xgboost установлен')"
python -c "import talib; print('✅ TA-Lib установлен')"

echo ""
echo "🎉 INSTALL OK"
echo ""
echo "📋 Следующие шаги:"
echo "   1. Настройте API ключи в config_futures.json"
echo "   2. Запустите: ./run_futures.sh"
echo "   3. Для активации окружения используйте: source freqtrade_venv/bin/activate"
echo ""
echo "📁 Структура проекта создана:"
echo "   ├── freqtrade/          # Основной код Freqtrade"
echo "   ├── freqtrade_venv/     # Виртуальное окружение"
echo "   ├── strategies/         # Торговые стратегии"
echo "   ├── signals/            # Модули внешних сигналов"
echo "   ├── logs/               # Логи"
echo "   └── user_data/          # Пользовательские данные"
echo ""