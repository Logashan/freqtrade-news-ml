"""
Модуль для получения сигналов от Helius API (Solana blockchain)
Анализирует крупные транзакции и DEX активность для SOL и связанных токенов

Автор: Trading Bot
Версия: 1.0
"""

import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import json


class HeliusSignalGenerator:
    """
    Генератор торговых сигналов на основе данных Helius API
    Отслеживает крупные транзакции и активность DEX на Solana
    """
    
    def __init__(self, api_key: str):
        """
        Инициализация генератора сигналов Helius
        
        Args:
            api_key: API ключ для Helius
        """
        self.api_key = api_key
        self.base_url = "https://api.helius.xyz/v0"
        self.session = requests.Session()
        
        # Настройки для анализа
        self.large_transaction_threshold = 100000  # $100K USD
        self.timeframe_minutes = 15  # Анализируем последние 15 минут
        self.dex_volume_threshold = 1000000  # $1M объём на DEX
        
        # Кэширование для избежания избыточных запросов
        self.cache = {}
        self.cache_ttl = 300  # 5 минут
        
        logging.info("Helius Signal Generator инициализирован")

    def get_signal(self) -> int:
        """
        Получает торговый сигнал для SOL на основе on-chain активности
        
        Returns:
            int: 1 = покупать, 0 = нейтрально, -1 = продавать
        """
        try:
            # Проверяем кэш
            cache_key = f"helius_signal_{int(time.time() // self.cache_ttl)}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Получаем различные метрики
            large_tx_signal = self._analyze_large_transactions()
            dex_activity_signal = self._analyze_dex_activity()
            whale_movement_signal = self._analyze_whale_movements()
            
            # Комбинируем сигналы с весами
            combined_signal = (
                large_tx_signal * 0.4 +
                dex_activity_signal * 0.4 +
                whale_movement_signal * 0.2
            )
            
            # Преобразуем в дискретный сигнал
            if combined_signal > 0.6:
                final_signal = 1  # Покупать
            elif combined_signal < -0.6:
                final_signal = -1  # Продавать
            else:
                final_signal = 0  # Нейтрально
                
            # Кэшируем результат
            self.cache[cache_key] = final_signal
            
            logging.info(f"Helius сигнал: {final_signal} (составной: {combined_signal:.2f})")
            return final_signal
            
        except Exception as e:
            logging.error(f"Ошибка получения Helius сигнала: {e}")
            return 0

    def _analyze_large_transactions(self) -> float:
        """
        Анализирует крупные транзакции SOL
        
        Returns:
            float: Сигнал от -1 до 1
        """
        try:
            # Получаем крупные транзакции за последние 15 минут
            url = f"{self.base_url}/transactions"
            params = {
                "api-key": self.api_key,
                "limit": 100,
                "type": "TRANSFER"
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            transactions = response.json()
            
            buy_volume = 0
            sell_volume = 0
            current_time = datetime.now()
            
            for tx in transactions:
                # Проверяем время транзакции
                tx_time = datetime.fromtimestamp(tx.get('timestamp', 0))
                if (current_time - tx_time).total_seconds() > self.timeframe_minutes * 60:
                    continue
                
                # Анализируем направление и размер
                amount_usd = tx.get('nativeTransfers', [{}])[0].get('amount', 0) * self._get_sol_price()
                
                if amount_usd > self.large_transaction_threshold:
                    # Определяем направление (упрощённая логика)
                    if self._is_buying_transaction(tx):
                        buy_volume += amount_usd
                    else:
                        sell_volume += amount_usd
            
            # Вычисляем сигнал на основе дисбаланса
            total_volume = buy_volume + sell_volume
            if total_volume > 0:
                signal = (buy_volume - sell_volume) / total_volume
                return max(-1, min(1, signal))
            
            return 0
            
        except Exception as e:
            logging.error(f"Ошибка анализа крупных транзакций: {e}")
            return 0

    def _analyze_dex_activity(self) -> float:
        """
        Анализирует активность на DEX (Raydium, Orca, Jupiter)
        
        Returns:
            float: Сигнал от -1 до 1
        """
        try:
            # Получаем данные о свопах на DEX
            url = f"{self.base_url}/transactions"
            params = {
                "api-key": self.api_key,
                "limit": 50,
                "type": "SWAP"
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            swaps = response.json()
            
            sol_buy_volume = 0
            sol_sell_volume = 0
            current_time = datetime.now()
            
            for swap in swaps:
                # Проверяем время свопа
                swap_time = datetime.fromtimestamp(swap.get('timestamp', 0))
                if (current_time - swap_time).total_seconds() > self.timeframe_minutes * 60:
                    continue
                
                # Анализируем свопы с участием SOL
                if self._involves_sol(swap):
                    volume_usd = self._get_swap_volume_usd(swap)
                    
                    if self._is_sol_buy_swap(swap):
                        sol_buy_volume += volume_usd
                    else:
                        sol_sell_volume += volume_usd
            
            # Вычисляем сигнал
            total_volume = sol_buy_volume + sol_sell_volume
            if total_volume > self.dex_volume_threshold:
                signal = (sol_buy_volume - sol_sell_volume) / total_volume
                return max(-1, min(1, signal * 1.5))  # Усиливаем DEX сигнал
            
            return 0
            
        except Exception as e:
            logging.error(f"Ошибка анализа DEX активности: {e}")
            return 0

    def _analyze_whale_movements(self) -> float:
        """
        Анализирует движения китов (крупных держателей)
        
        Returns:
            float: Сигнал от -1 до 1
        """
        try:
            # Получаем информацию о крупных счетах
            url = f"{self.base_url}/addresses/balances"
            params = {
                "api-key": self.api_key,
                "addresses": self._get_known_whale_addresses()
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            balances = response.json()
            
            # Анализируем изменения балансов китов
            accumulation_score = 0
            distribution_score = 0
            
            for address_data in balances:
                balance_change = self._get_balance_change(address_data)
                
                if balance_change > 0:
                    accumulation_score += abs(balance_change)
                elif balance_change < 0:
                    distribution_score += abs(balance_change)
            
            # Вычисляем сигнал
            total_activity = accumulation_score + distribution_score
            if total_activity > 0:
                signal = (accumulation_score - distribution_score) / total_activity
                return max(-1, min(1, signal))
            
            return 0
            
        except Exception as e:
            logging.error(f"Ошибка анализа движений китов: {e}")
            return 0

    def _get_sol_price(self) -> float:
        """
        Получает текущую цену SOL в USD
        
        Returns:
            float: Цена SOL в USD
        """
        try:
            # Можно использовать публичные API для получения цены
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "solana",
                "vs_currencies": "usd"
            }
            
            response = self.session.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return data.get("solana", {}).get("usd", 0)
            
        except Exception as e:
            logging.error(f"Ошибка получения цены SOL: {e}")
            return 0

    def _is_buying_transaction(self, transaction: dict) -> bool:
        """
        Определяет, является ли транзакция покупкой SOL
        
        Args:
            transaction: Данные транзакции
            
        Returns:
            bool: True если покупка, False если продажа
        """
        # Упрощённая логика - в реальности нужен более сложный анализ
        # на основе адресов отправителя и получателя
        
        try:
            native_transfers = transaction.get('nativeTransfers', [])
            if not native_transfers:
                return True  # По умолчанию считаем покупкой
                
            # Анализируем первый трансфер
            first_transfer = native_transfers[0]
            from_address = first_transfer.get('fromUserAccount', '')
            to_address = first_transfer.get('toUserAccount', '')
            
            # Если отправитель - известная биржа, то это вероятно продажа
            known_exchange_addresses = self._get_known_exchange_addresses()
            if from_address in known_exchange_addresses:
                return False
                
            # Если получатель - биржа, то это покупка
            if to_address in known_exchange_addresses:
                return True
                
            return True  # По умолчанию
            
        except Exception:
            return True

    def _involves_sol(self, swap: dict) -> bool:
        """
        Проверяет, участвует ли SOL в свопе
        
        Args:
            swap: Данные свопа
            
        Returns:
            bool: True если SOL участвует в свопе
        """
        try:
            token_transfers = swap.get('tokenTransfers', [])
            
            for transfer in token_transfers:
                mint = transfer.get('mint', '')
                # SOL имеет специальный mint адрес
                if mint == 'So11111111111111111111111111111111111111112':
                    return True
                    
            return False
            
        except Exception:
            return False

    def _is_sol_buy_swap(self, swap: dict) -> bool:
        """
        Определяет, является ли свап покупкой SOL
        
        Args:
            swap: Данные свопа
            
        Returns:
            bool: True если покупка SOL
        """
        try:
            token_transfers = swap.get('tokenTransfers', [])
            
            sol_amount = 0
            other_token_amount = 0
            
            for transfer in token_transfers:
                amount = transfer.get('tokenAmount', 0)
                mint = transfer.get('mint', '')
                
                if mint == 'So11111111111111111111111111111111111111112':
                    sol_amount += amount
                else:
                    other_token_amount += amount
            
            # Если получили SOL больше чем отдали, то это покупка
            return sol_amount > 0
            
        except Exception:
            return True

    def _get_swap_volume_usd(self, swap: dict) -> float:
        """
        Вычисляет объём свопа в USD
        
        Args:
            swap: Данные свопа
            
        Returns:
            float: Объём в USD
        """
        try:
            token_transfers = swap.get('tokenTransfers', [])
            sol_price = self._get_sol_price()
            
            total_volume = 0
            
            for transfer in token_transfers:
                amount = transfer.get('tokenAmount', 0)
                mint = transfer.get('mint', '')
                
                if mint == 'So11111111111111111111111111111111111111112':
                    # SOL
                    total_volume += abs(amount) * sol_price
                else:
                    # Другие токены - приблизительная оценка
                    total_volume += abs(amount) * 1  # Упрощение
            
            return total_volume / 2  # Делим на 2, т.к. считали и input и output
            
        except Exception:
            return 0

    def _get_known_whale_addresses(self) -> List[str]:
        """
        Возвращает список известных адресов китов SOL
        
        Returns:
            List[str]: Список адресов
        """
        # В реальной реализации это должна быть база данных
        # известных крупных держателей SOL
        return [
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",  # Пример
            "3LAzExbwvP8VcVKCYH2TSoMxX6QHNZqPjAQnJdJK6YLA",  # Пример
            # Добавить реальные адреса китов
        ]

    def _get_known_exchange_addresses(self) -> List[str]:
        """
        Возвращает список известных адресов бирж
        
        Returns:
            List[str]: Список адресов бирж
        """
        return [
            "FWYq7ecnDCH4YbV7FjqGpJvaKNGfKPZWgJYk5zS5mZQz",  # Binance
            "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2",  # FTX (исторический)
            # Добавить другие известные адреса бирж
        ]

    def _get_balance_change(self, address_data: dict) -> float:
        """
        Вычисляет изменение баланса для адреса
        
        Args:
            address_data: Данные адреса
            
        Returns:
            float: Изменение баланса
        """
        try:
            # В реальной реализации здесь должно быть сравнение
            # с предыдущими сохранёнными данными
            current_balance = address_data.get('balance', 0)
            
            # Пока возвращаем 0 (нет изменений)
            # В будущем нужно сохранять и сравнивать исторические данные
            return 0
            
        except Exception:
            return 0

    def get_detailed_analysis(self) -> Dict:
        """
        Возвращает детальный анализ для логирования
        
        Returns:
            Dict: Подробная информация об анализе
        """
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "large_transactions": self._analyze_large_transactions(),
                "dex_activity": self._analyze_dex_activity(), 
                "whale_movements": self._analyze_whale_movements(),
                "sol_price": self._get_sol_price(),
                "timeframe_minutes": self.timeframe_minutes
            }
        except Exception as e:
            logging.error(f"Ошибка детального анализа Helius: {e}")
            return {}