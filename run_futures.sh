#!/bin/bash

# Запускной скрипт для торгового бота Freqtrade (фьючерсы Bybit)
# Автор: Trading Bot
# Версия: 1.0

echo "🚀 Запуск торгового бота Freqtrade для фьючерсов Bybit..."

# Настройки
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/freqtrade_venv"
CONFIG_FILE="$PROJECT_DIR/config_futures.json"
STRATEGY_DIR="$PROJECT_DIR/strategies"
LOG_DIR="$PROJECT_DIR/logs"
DATE_STAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/freqtrade_$DATE_STAMP.log"

# Проверяем наличие необходимых файлов и директорий
echo "🔍 Проверяем наличие необходимых компонентов..."

if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Виртуальное окружение не найдено в $VENV_DIR"
    echo "   Запустите сначала: ./install_freqtrade.sh"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Файл конфигурации не найден: $CONFIG_FILE"
    exit 1
fi

if [ ! -d "$STRATEGY_DIR" ]; then
    echo "❌ Директория стратегий не найдена: $STRATEGY_DIR"
    exit 1
fi

# Создаём директорию логов если её нет
mkdir -p "$LOG_DIR"

# Активируем виртуальное окружение
echo "⚡ Активируем виртуальное окружение..."
source "$VENV_DIR/bin/activate"

if [ $? -ne 0 ]; then
    echo "❌ Ошибка активации виртуального окружения"
    exit 1
fi

# Определяем команду Freqtrade (CLI или модуль)
echo "🔍 Проверяем установку Freqtrade..."
if command -v freqtrade >/dev/null 2>&1; then
    FREQTRADE_CMD="freqtrade"
else
    FREQTRADE_CMD="python -m freqtrade"
fi

# Проверяем версию
$FREQTRADE_CMD --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Freqtrade не установлен или не работает"
    echo "   Запустите переустановку: ./install_freqtrade.sh"
    exit 1
fi
echo "✅ Freqtrade найден: $($FREQTRADE_CMD --version 2>/dev/null)"

# Проверяем наличие стратегии
STRATEGY_FILE="$STRATEGY_DIR/NewsHeliusBitqueryML.py"
if [ ! -f "$STRATEGY_FILE" ]; then
    echo "❌ Файл стратегии не найден: $STRATEGY_FILE"
    exit 1
fi

# Проверяем конфигурацию
echo "🔍 Валидируем конфигурацию..."
python -c "
import json
try:
    with open('$CONFIG_FILE', 'r') as f:
        config = json.load(f)
    print('✅ Конфигурация валидна')
    
    # Проверяем ключевые параметры
    if config.get('dry_run', True):
        print('⚠️  Режим: DRY RUN (демо торговля)')
    else:
        print('🔥 Режим: LIVE TRADING (реальные сделки)')
        
    print(f'📊 Торговые пары: {len(config.get(\"pair_whitelist\", []))}')
    print(f'💰 Стейк валюта: {config.get(\"stake_currency\", \"N/A\")}')
    print(f'📈 Плечо: {config.get(\"leverage\", \"N/A\")}x')
    print(f'🛡️  Стоп-лосс: {config.get(\"stoploss\", \"N/A\")}')
    
except Exception as e:
    print(f'❌ Ошибка конфигурации: {e}')
    exit(1)
" || exit 1

# Выводим важное предупреждение
echo ""
echo "⚠️  ВАЖНЫЕ ПРЕДУПРЕЖДЕНИЯ:"
echo "   1. Убедитесь, что API ключи Bybit настроены правильно"
echo "   2. Рекомендуется начать с dry_run=true для тестирования"
echo "   3. Следите за логами и производительностью стратегии"
echo "   4. Торговля фьючерсами связана с высокими рисками"
echo ""

# Запрашиваем подтверждение (только в интерактивном режиме)
if [ -t 0 ]; then
    read -p "Продолжить запуск бота? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Запуск отменён пользователем"
        exit 1
    fi
fi

echo ""
echo "🎯 Параметры запуска:"
echo "   Конфиг: $CONFIG_FILE"
echo "   Стратегия: NewsHeliusBitqueryML"
echo "   Лог файл: $LOG_FILE"
echo "   Время запуска: $(date)"
echo ""

# Функция для корректной остановки
cleanup() {
    echo ""
    echo "🛑 Получен сигнал остановки. Завершаем работу бота..."
    
    # Отправляем сигнал завершения процессу freqtrade
    if [ ! -z "$FREQTRADE_PID" ]; then
        kill -TERM "$FREQTRADE_PID" 2>/dev/null
        
        # Ждём корректного завершения до 30 секунд
        for i in {1..30}; do
            if ! kill -0 "$FREQTRADE_PID" 2>/dev/null; then
                break
            fi
            echo "⏳ Ожидание завершения... ($i/30)"
            sleep 1
        done
        
        # Принудительно завершаем если не остановился
        if kill -0 "$FREQTRADE_PID" 2>/dev/null; then
            echo "🔪 Принудительное завершение процесса"
            kill -KILL "$FREQTRADE_PID" 2>/dev/null
        fi
    fi
    
    echo "✅ Бот остановлен. Лог сохранён в: $LOG_FILE"
    exit 0
}

# Устанавливаем обработчики сигналов
trap cleanup SIGINT SIGTERM

echo "🚀 Запускаем Freqtrade..."
echo "   Для остановки используйте Ctrl+C"
echo "   Логи сохраняются в $LOG_FILE"
echo ""

# Запускаем Freqtrade в фоновом режиме с перенаправлением вывода
$FREQTRADE_CMD trade \
  --config "$CONFIG_FILE" \
  --strategy NewsHeliusBitqueryML \
  --strategy-path "$STRATEGY_DIR" \
  --verbosity 3 \
  --logfile "$LOG_FILE" &

# Сохраняем PID процесса
FREQTRADE_PID=$!

# Проверяем, что процесс запустился
sleep 3
if ! kill -0 "$FREQTRADE_PID" 2>/dev/null; then
    echo "❌ Ошибка запуска Freqtrade. Проверьте лог:"
    echo "   tail -n 20 $LOG_FILE"
    exit 1
fi

echo "✅ Freqtrade запущен успешно (PID: $FREQTRADE_PID)"
echo ""
echo "📊 Полезные команды во время работы:"
echo "   Просмотр логов:        tail -f $LOG_FILE"
echo "   Статус бота:           freqtrade status"
echo "   Баланс:                freqtrade balance" 
echo "   Открытые сделки:       freqtrade show_trades"
echo "   Производительность:    freqtrade profit"
echo ""
echo "🌐 Веб-интерфейс (если включён в конфиге):"
echo "   http://localhost:8080"
echo ""

# Функция для мониторинга состояния
monitor_bot() {
    local last_check=$(date +%s)
    local check_interval=300  # 5 минут
    
    while true; do
        sleep 60  # Проверяем каждую минуту
        
        # Проверяем, что процесс ещё работает
        if ! kill -0 "$FREQTRADE_PID" 2>/dev/null; then
            echo "❌ Процесс Freqtrade завершился неожиданно!"
            echo "   Проверьте лог: tail -n 50 $LOG_FILE"
            exit 1
        fi
        
        # Периодически выводим статистику
        local current_time=$(date +%s)
        if [ $((current_time - last_check)) -ge $check_interval ]; then
            echo "📊 $(date): Бот работает (PID: $FREQTRADE_PID)"
            
            # Показываем размер лог файла
            if [ -f "$LOG_FILE" ]; then
                local log_size=$(du -h "$LOG_FILE" | cut -f1)
                echo "   Размер лога: $log_size"
            fi
            
            # Показываем использование памяти процессом
            local memory_usage=$(ps -o rss= -p "$FREQTRADE_PID" 2>/dev/null | awk '{print $1/1024 "MB"}')
            if [ ! -z "$memory_usage" ]; then
                echo "   Использование памяти: $memory_usage"
            fi
            
            last_check=$current_time
        fi
    done
}

# Запускаем мониторинг
monitor_bot

# Эта строка не должна выполниться при нормальной работе
echo "❌ Неожиданный выход из скрипта"
exit 1