#!/bin/bash

# Скрипт для запуска торгового бота
# Автор: Trading Bot
# Версия: 1.0

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка наличия виртуального окружения
check_venv() {
    if [ ! -d "freqtrade_venv" ]; then
        print_error "Виртуальное окружение не найдено!"
        print_info "Создайте виртуальное окружение:"
        echo "python3 -m venv freqtrade_venv"
        echo "source freqtrade_venv/bin/activate"
        echo "pip install -r requirements.txt"
        exit 1
    fi
}

# Проверка конфигурации
check_config() {
    if [ ! -f "config_backtest.json" ]; then
        print_error "Конфигурационный файл config_backtest.json не найден!"
        exit 1
    fi
    
    if [ ! -f "_newconfig.json" ]; then
        print_warning "Основной конфигурационный файл _newconfig.json не найден!"
        print_info "Используется config_backtest.json"
    fi
}

# Проверка стратегии
check_strategy() {
    if [ ! -f "strategies/NewsHeliusBitqueryML.py" ]; then
        print_error "Стратегия NewsHeliusBitqueryML.py не найдена!"
        exit 1
    fi
}

# Создание директорий
create_directories() {
    print_info "Создание необходимых директорий..."
    mkdir -p logs
    mkdir -p user_data/backtest_results
    mkdir -p user_data/freqaimodels
    mkdir -p user_data/data
    print_success "Директории созданы"
}

# Активация виртуального окружения
activate_venv() {
    print_info "Активация виртуального окружения..."
    source freqtrade_venv/bin/activate
    print_success "Виртуальное окружение активировано"
}

# Проверка зависимостей
check_dependencies() {
    print_info "Проверка зависимостей..."
    
    # Проверяем основные пакеты
    python -c "import freqtrade" 2>/dev/null || {
        print_error "FreqTrade не установлен!"
        print_info "Установите FreqTrade: pip install freqtrade"
        exit 1
    }
    
    python -c "import sklearn" 2>/dev/null || {
        print_warning "scikit-learn не установлен"
        print_info "Установка: pip install scikit-learn"
        pip install scikit-learn
    }
    
    python -c "import textblob" 2>/dev/null || {
        print_warning "textblob не установлен"
        print_info "Установка: pip install textblob"
        pip install textblob
    }
    
    print_success "Зависимости проверены"
}

# Функция для выбора режима
select_mode() {
    echo -e "\n${BLUE}Выберите режим работы:${NC}"
    echo "1) Dry-run (тестовый режим)"
    echo "2) Live trading (реальная торговля)"
    echo "3) Backtesting (бэктестинг)"
    echo "4) Hyperopt (оптимизация)"
    echo "5) Monitor (мониторинг)"
    echo "6) Exit"
    
    read -p "Введите номер (1-6): " choice
    
    case $choice in
        1)
            print_info "Запуск в dry-run режиме..."
            run_dry_run
            ;;
        2)
            print_warning "ВНИМАНИЕ: Реальная торговля!"
            read -p "Вы уверены? (y/N): " confirm
            if [[ $confirm == [yY] ]]; then
                run_live_trading
            else
                print_info "Отменено"
                exit 0
            fi
            ;;
        3)
            print_info "Запуск бэктестинга..."
            run_backtesting
            ;;
        4)
            print_info "Запуск гипероптимизации..."
            run_hyperopt
            ;;
        5)
            print_info "Запуск мониторинга..."
            run_monitor
            ;;
        6)
            print_info "Выход"
            exit 0
            ;;
        *)
            print_error "Неверный выбор"
            select_mode
            ;;
    esac
}

# Dry-run режим
run_dry_run() {
    print_info "Запуск FreqTrade в dry-run режиме..."
    freqtrade trade \
        --config config_backtest.json \
        --strategy NewsHeliusBitqueryML \
        --logfile logs/freqtrade_$(date +%Y%m%d_%H%M%S).log
}

# Реальная торговля
run_live_trading() {
    print_info "Запуск FreqTrade в режиме реальной торговли..."
    freqtrade trade \
        --config _newconfig.json \
        --strategy NewsHeliusBitqueryML \
        --logfile logs/freqtrade_$(date +%Y%m%d_%H%M%S).log
}

# Бэктестинг
run_backtesting() {
    print_info "Запуск бэктестинга..."
    python backtest_strategy.py
}

# Гипероптимизация
run_hyperopt() {
    print_info "Запуск гипероптимизации..."
    python backtest_strategy.py --hyperopt --epochs 100
}

# Мониторинг
run_monitor() {
    print_info "Запуск мониторинга..."
    python bot_monitor.py
}

# Основная функция
main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}   Новый Фриг Бот - Запуск${NC}"
    echo -e "${BLUE}================================${NC}"
    
    # Проверки
    check_venv
    check_config
    check_strategy
    
    # Создание директорий
    create_directories
    
    # Активация окружения
    activate_venv
    
    # Проверка зависимостей
    check_dependencies
    
    # Выбор режима
    select_mode
}

# Обработка сигналов
trap 'print_info "Получен сигнал остановки. Завершение работы..."; exit 0' SIGINT SIGTERM

# Запуск основной функции
main "$@"
