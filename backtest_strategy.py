#!/usr/bin/env python3
"""
Скрипт для тестирования торговой стратегии NewsHeliusBitqueryML
Выполняет backtesting на исторических данных с различными параметрами

Автор: Trading Bot
Версия: 2.0
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
import subprocess
import argparse
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest.log'),
        logging.StreamHandler()
    ]
)

def run_backtest(config_file: str, strategy: str, timerange: str = None, 
                pairs: list = None, timeframe: str = "5m") -> bool:
    """
    Запускает бэктестинг с заданными параметрами
    
    Args:
        config_file: Путь к конфигурационному файлу
        strategy: Название стратегии
        timerange: Временной диапазон (например, "20240101-20241231")
        pairs: Список торговых пар
        timeframe: Таймфрейм
        
    Returns:
        bool: True если бэктестинг прошёл успешно
    """
    try:
        # Формируем команду
        cmd = [
            "freqtrade", "backtesting",
            "--config", config_file,
            "--strategy", strategy,
            "--timeframe", timeframe
        ]
        
        if timerange:
            cmd.extend(["--timerange", timerange])
            
        if pairs:
            pairs_str = ",".join(pairs)
            cmd.extend(["--pairs", pairs_str])
            
        # Добавляем дополнительные параметры для детального анализа
        cmd.extend([
            "--export", "trades",
            "--export-filename", f"user_data/backtest_results/backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "--breakdown", "day",
            "--cache", "day"
        ])
        
        logging.info(f"Запускаем бэктестинг: {' '.join(cmd)}")
        
        # Запускаем команду
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("Бэктестинг завершён успешно")
            logging.info(result.stdout)
            return True
        else:
            logging.error(f"Ошибка бэктестинга: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"Ошибка запуска бэктестинга: {e}")
        return False

def run_hyperopt(config_file: str, strategy: str, timerange: str = None,
                epochs: int = 100, spaces: list = None) -> bool:
    """
    Запускает гипероптимизацию стратегии
    
    Args:
        config_file: Путь к конфигурационному файлу
        strategy: Название стратегии
        timerange: Временной диапазон
        epochs: Количество эпох оптимизации
        spaces: Список пространств для оптимизации
        
    Returns:
        bool: True если гипероптимизация прошла успешно
    """
    try:
        cmd = [
            "freqtrade", "hyperopt",
            "--config", config_file,
            "--strategy", strategy,
            "--epochs", str(epochs)
        ]
        
        if timerange:
            cmd.extend(["--timerange", timerange])
            
        if spaces:
            spaces_str = ",".join(spaces)
            cmd.extend(["--spaces", spaces_str])
            
        logging.info(f"Запускаем гипероптимизацию: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("Гипероптимизация завершена успешно")
            return True
        else:
            logging.error(f"Ошибка гипероптимизации: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"Ошибка запуска гипероптимизации: {e}")
        return False

def analyze_results(results_dir: str) -> dict:
    """
    Анализирует результаты бэктестинга
    
    Args:
        results_dir: Директория с результатами
        
    Returns:
        dict: Анализ результатов
    """
    try:
        analysis = {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_profit": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }
        
        # Здесь можно добавить парсинг результатов бэктестинга
        # FreqTrade сохраняет результаты в JSON формате
        
        return analysis
        
    except Exception as e:
        logging.error(f"Ошибка анализа результатов: {e}")
        return {}

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Скрипт для бэктестинга торговой стратегии")
    parser.add_argument("--config", default="config_backtest.json", help="Конфигурационный файл")
    parser.add_argument("--strategy", default="NewsHeliusBitqueryML", help="Название стратегии")
    parser.add_argument("--timerange", help="Временной диапазон (например, 20240101-20241231)")
    parser.add_argument("--pairs", nargs="+", help="Список торговых пар")
    parser.add_argument("--timeframe", default="5m", help="Таймфрейм")
    parser.add_argument("--hyperopt", action="store_true", help="Запустить гипероптимизацию")
    parser.add_argument("--epochs", type=int, default=100, help="Количество эпох для гипероптимизации")
    parser.add_argument("--spaces", nargs="+", default=["buy", "sell"], help="Пространства для оптимизации")
    
    args = parser.parse_args()
    
    # Создаём директории если их нет
    os.makedirs("logs", exist_ok=True)
    os.makedirs("user_data/backtest_results", exist_ok=True)
    
    logging.info("Начинаем тестирование стратегии")
    
    if args.hyperopt:
        # Запускаем гипероптимизацию
        success = run_hyperopt(
            args.config, 
            args.strategy, 
            args.timerange, 
            args.epochs, 
            args.spaces
        )
    else:
        # Запускаем бэктестинг
        success = run_backtest(
            args.config,
            args.strategy,
            args.timerange,
            args.pairs,
            args.timeframe
        )
    
    if success:
        logging.info("Тестирование завершено успешно")
        
        # Анализируем результаты
        results_dir = "user_data/backtest_results"
        analysis = analyze_results(results_dir)
        
        logging.info("Результаты анализа:")
        for key, value in analysis.items():
            logging.info(f"{key}: {value}")
    else:
        logging.error("Тестирование завершилось с ошибкой")
        sys.exit(1)

if __name__ == "__main__":
    main()
