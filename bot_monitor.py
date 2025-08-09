#!/usr/bin/env python3
"""
Скрипт для мониторинга и управления торговым ботом
Отслеживает состояние бота, анализирует производительность и отправляет уведомления

Автор: Trading Bot
Версия: 1.0
"""

import os
import sys
import json
import time
import logging
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse
import subprocess
from pathlib import Path


class BotMonitor:
    """
    Класс для мониторинга торгового бота
    """
    
    def __init__(self, config_file: str = "config_backtest.json"):
        """
        Инициализация монитора
        
        Args:
            config_file: Путь к конфигурационному файлу
        """
        self.config_file = config_file
        self.config = self._load_config()
        
        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/monitor.log'),
                logging.StreamHandler()
            ]
        )
        
        # Параметры мониторинга
        self.check_interval = 60  # секунды
        self.alert_thresholds = {
            "max_drawdown": -0.1,  # -10%
            "consecutive_losses": 5,
            "profit_threshold": 0.02,  # 2%
            "volume_threshold": 1000  # $1000
        }
        
        # Состояние бота
        self.bot_status = "unknown"
        self.last_check = None
        
        logging.info("Bot Monitor инициализирован")

    def _load_config(self) -> dict:
        """Загружает конфигурацию"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки конфигурации: {e}")
            return {}

    def check_bot_status(self) -> str:
        """
        Проверяет статус бота
        
        Returns:
            str: Статус бота (running, stopped, error)
        """
        try:
            # Проверяем процесс бота
            result = subprocess.run(
                ["pgrep", "-f", "freqtrade"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.bot_status = "running"
                logging.info("Бот работает")
            else:
                self.bot_status = "stopped"
                logging.warning("Бот остановлен")
                
            return self.bot_status
            
        except Exception as e:
            logging.error(f"Ошибка проверки статуса бота: {e}")
            self.bot_status = "error"
            return self.bot_status

    def get_trade_statistics(self) -> Dict:
        """
        Получает статистику торговли
        
        Returns:
            Dict: Статистика торговли
        """
        try:
            # Путь к базе данных
            db_path = "user_data/tradesv3.sqlite"
            
            if not os.path.exists(db_path):
                logging.warning("База данных не найдена")
                return {}
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Получаем общую статистику
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit_ratio > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN profit_ratio < 0 THEN 1 ELSE 0 END) as losing_trades,
                    AVG(profit_ratio) as avg_profit,
                    SUM(profit_ratio) as total_profit,
                    MIN(profit_ratio) as max_loss,
                    MAX(profit_ratio) as max_profit
                FROM trades
                WHERE close_date IS NOT NULL
            """)
            
            row = cursor.fetchone()
            if row:
                stats = {
                    "total_trades": row[0],
                    "winning_trades": row[1],
                    "losing_trades": row[2],
                    "avg_profit": row[3] or 0,
                    "total_profit": row[4] or 0,
                    "max_loss": row[5] or 0,
                    "max_profit": row[6] or 0
                }
                
                # Вычисляем дополнительные метрики
                if stats["total_trades"] > 0:
                    stats["win_rate"] = stats["winning_trades"] / stats["total_trades"]
                    stats["profit_factor"] = (
                        abs(stats["max_profit"]) / abs(stats["max_loss"]) 
                        if stats["max_loss"] != 0 else 0
                    )
                else:
                    stats["win_rate"] = 0
                    stats["profit_factor"] = 0
                    
            else:
                stats = {}
                
            # Получаем статистику за последние 24 часа
            cursor.execute("""
                SELECT 
                    COUNT(*) as recent_trades,
                    SUM(profit_ratio) as recent_profit
                FROM trades
                WHERE close_date >= datetime('now', '-1 day')
            """)
            
            recent_row = cursor.fetchone()
            if recent_row:
                stats["recent_trades"] = recent_row[0]
                stats["recent_profit"] = recent_row[1] or 0
            else:
                stats["recent_trades"] = 0
                stats["recent_profit"] = 0
                
            conn.close()
            return stats
            
        except Exception as e:
            logging.error(f"Ошибка получения статистики: {e}")
            return {}

    def calculate_drawdown(self) -> float:
        """
        Вычисляет максимальную просадку
        
        Returns:
            float: Максимальная просадка в процентах
        """
        try:
            db_path = "user_data/tradesv3.sqlite"
            
            if not os.path.exists(db_path):
                return 0.0
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Получаем кумулятивную прибыль по времени
            cursor.execute("""
                SELECT 
                    close_date,
                    SUM(profit_ratio) OVER (ORDER BY close_date) as cumulative_profit
                FROM trades
                WHERE close_date IS NOT NULL
                ORDER BY close_date
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return 0.0
                
            # Вычисляем просадку
            peak = 0.0
            max_drawdown = 0.0
            
            for _, cumulative_profit in rows:
                if cumulative_profit > peak:
                    peak = cumulative_profit
                else:
                    drawdown = (peak - cumulative_profit) / peak if peak > 0 else 0
                    max_drawdown = max(max_drawdown, drawdown)
                    
            return max_drawdown
            
        except Exception as e:
            logging.error(f"Ошибка вычисления просадки: {e}")
            return 0.0

    def check_alerts(self, stats: Dict) -> List[str]:
        """
        Проверяет условия для алертов
        
        Args:
            stats: Статистика торговли
            
        Returns:
            List[str]: Список алертов
        """
        alerts = []
        
        try:
            # Проверяем просадку
            drawdown = self.calculate_drawdown()
            if drawdown < self.alert_thresholds["max_drawdown"]:
                alerts.append(f"Критическая просадка: {drawdown:.2%}")
                
            # Проверяем последовательные убытки
            if stats.get("losing_trades", 0) >= self.alert_thresholds["consecutive_losses"]:
                alerts.append(f"Много убыточных сделок: {stats['losing_trades']}")
                
            # Проверяем прибыльность
            if stats.get("total_profit", 0) < self.alert_thresholds["profit_threshold"]:
                alerts.append(f"Низкая прибыльность: {stats['total_profit']:.2%}")
                
            # Проверяем статус бота
            if self.bot_status != "running":
                alerts.append(f"Бот не работает: {self.bot_status}")
                
        except Exception as e:
            logging.error(f"Ошибка проверки алертов: {e}")
            
        return alerts

    def send_notification(self, message: str, level: str = "info"):
        """
        Отправляет уведомление
        
        Args:
            message: Текст сообщения
            level: Уровень важности (info, warning, error)
        """
        try:
            # Здесь можно добавить отправку в Telegram, Discord, email и т.д.
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"[{timestamp}] {level.upper()}: {message}"
            
            logging.info(formatted_message)
            
            # Пример отправки в Telegram (если настроено)
            if self.config.get("telegram", {}).get("enabled"):
                self._send_telegram_message(formatted_message)
                
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления: {e}")

    def _send_telegram_message(self, message: str):
        """Отправляет сообщение в Telegram"""
        try:
            telegram_config = self.config.get("telegram", {})
            token = telegram_config.get("token")
            chat_id = telegram_config.get("chat_id")
            
            if token and chat_id:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }
                
                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()
                
        except Exception as e:
            logging.error(f"Ошибка отправки в Telegram: {e}")

    def generate_report(self) -> Dict:
        """
        Генерирует отчёт о состоянии бота
        
        Returns:
            Dict: Отчёт
        """
        try:
            stats = self.get_trade_statistics()
            drawdown = self.calculate_drawdown()
            alerts = self.check_alerts(stats)
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "bot_status": self.bot_status,
                "statistics": stats,
                "drawdown": drawdown,
                "alerts": alerts,
                "uptime": self._get_uptime()
            }
            
            return report
            
        except Exception as e:
            logging.error(f"Ошибка генерации отчёта: {e}")
            return {}

    def _get_uptime(self) -> str:
        """Получает время работы бота"""
        try:
            result = subprocess.run(
                ["ps", "-eo", "pid,etime,cmd"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'freqtrade' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]
                            
            return "unknown"
            
        except Exception as e:
            logging.error(f"Ошибка получения uptime: {e}")
            return "unknown"

    def start_monitoring(self, interval: int = None):
        """
        Запускает мониторинг
        
        Args:
            interval: Интервал проверки в секундах
        """
        if interval:
            self.check_interval = interval
            
        logging.info(f"Запускаем мониторинг с интервалом {self.check_interval} секунд")
        
        try:
            while True:
                # Проверяем статус бота
                self.check_bot_status()
                
                # Получаем статистику
                stats = self.get_trade_statistics()
                
                # Проверяем алерты
                alerts = self.check_alerts(stats)
                
                # Отправляем уведомления если есть алерты
                for alert in alerts:
                    self.send_notification(alert, "warning")
                    
                # Генерируем отчёт каждый час
                if not self.last_check or (datetime.now() - self.last_check).seconds >= 3600:
                    report = self.generate_report()
                    logging.info(f"Отчёт: {json.dumps(report, indent=2)}")
                    self.last_check = datetime.now()
                    
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logging.info("Мониторинг остановлен пользователем")
        except Exception as e:
            logging.error(f"Ошибка мониторинга: {e}")


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Мониторинг торгового бота")
    parser.add_argument("--config", default="config_backtest.json", help="Конфигурационный файл")
    parser.add_argument("--interval", type=int, default=60, help="Интервал проверки в секундах")
    parser.add_argument("--report", action="store_true", help="Сгенерировать отчёт и выйти")
    
    args = parser.parse_args()
    
    # Создаём директории
    os.makedirs("logs", exist_ok=True)
    
    # Создаём монитор
    monitor = BotMonitor(args.config)
    
    if args.report:
        # Генерируем отчёт
        report = monitor.generate_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        # Запускаем мониторинг
        monitor.start_monitoring(args.interval)


if __name__ == "__main__":
    main()
