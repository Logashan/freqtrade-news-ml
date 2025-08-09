"""
Модуль для получения сигналов от Bitquery API
Анализирует крупные inflow/outflow по различным криптовалютным парам

Автор: Trading Bot
Версия: 1.0
"""

import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import json


class BitquerySignalGenerator:
    """
    Генератор торговых сигналов на основе данных Bitquery API
    Отслеживает крупные движения средств, активность на DEX и накопление/распределение
    """
    
    def __init__(self, api_key: str):
        """
        Инициализация генератора сигналов Bitquery
        
        Args:
            api_key: API ключ для Bitquery
        """
        self.api_key = api_key
        self.base_url = "https://graphql.bitquery.io"
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        })
        
        # Настройки для анализа
        self.large_flow_threshold = 500000  # $500K USD
        self.timeframe_hours = 6  # Анализируем последние 6 часов
        self.dex_volume_threshold = 2000000  # $2M объём на DEX
        
        # Кэширование для избежания избыточных запросов
        self.cache = {}
        self.cache_ttl = 600  # 10 минут
        
        # Mapping токенов на их контракты
        self.token_contracts = {
            "BTC": "bitcoin",
            "ETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH
            "ADA": "0x3ee2200efb3400fabb9aacf31297cbdd1d435d47",  # ADA на BSC
            "LINK": "0x514910771af9ca656af840dff83e8264ecf986ca",
            "XRP": "ripple",
            "DOGE": "dogecoin",
            "SOL": "solana"
        }
        
        logging.info("Bitquery Signal Generator инициализирован")

    def get_signal(self, trading_pair: str) -> int:
        """
        Получает торговый сигнал для заданной пары на основе on-chain активности
        
        Args:
            trading_pair: Торговая пара (например, "BTC/USDT:USDT")
            
        Returns:
            int: 1 = покупать, 0 = нейтрально, -1 = продавать
        """
        try:
            # Извлекаем базовую валюту из пары
            base_currency = self._extract_base_currency(trading_pair)
            
            # Проверяем кэш
            cache_key = f"bitquery_signal_{base_currency}_{int(time.time() // self.cache_ttl)}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Получаем различные метрики
            inflow_outflow_signal = self._analyze_inflow_outflow(base_currency)
            dex_activity_signal = self._analyze_dex_activity(base_currency)
            whale_accumulation_signal = self._analyze_whale_accumulation(base_currency)
            exchange_flows_signal = self._analyze_exchange_flows(base_currency)
            
            # Комбинируем сигналы с весами
            combined_signal = (
                inflow_outflow_signal * 0.3 +
                dex_activity_signal * 0.25 +
                whale_accumulation_signal * 0.25 +
                exchange_flows_signal * 0.2
            )
            
            # Преобразуем в дискретный сигнал
            if combined_signal > 0.5:
                final_signal = 1  # Покупать
            elif combined_signal < -0.5:
                final_signal = -1  # Продавать
            else:
                final_signal = 0  # Нейтрально
                
            # Кэшируем результат
            self.cache[cache_key] = final_signal
            
            logging.info(f"Bitquery сигнал для {base_currency}: {final_signal} (составной: {combined_signal:.2f})")
            return final_signal
            
        except Exception as e:
            logging.error(f"Ошибка получения Bitquery сигнала для {trading_pair}: {e}")
            return 0

    def _extract_base_currency(self, trading_pair: str) -> str:
        """
        Извлекает базовую валюту из торговой пары
        
        Args:
            trading_pair: Торговая пара
            
        Returns:
            str: Базовая валюта
        """
        # Примеры: "BTC/USDT:USDT" -> "BTC", "ETH/USDT:USDT" -> "ETH"
        if '/' in trading_pair:
            return trading_pair.split('/')[0]
        elif '_' in trading_pair:
            return trading_pair.split('_')[0]
        else:
            return trading_pair

    def _analyze_inflow_outflow(self, currency: str) -> float:
        """
        Анализирует inflow/outflow для валюты
        
        Args:
            currency: Базовая валюта
            
        Returns:
            float: Сигнал от -1 до 1
        """
        try:
            # GraphQL запрос для анализа потоков
            query = """
            query ($currency: String!, $from: ISO8601DateTime!, $till: ISO8601DateTime!) {
              ethereum(network: ethereum) {
                transfers(
                  currency: {symbol: {is: $currency}}
                  date: {between: [$from, $till]}
                  amount: {gt: 100}
                ) {
                  sum: amount(calculate: sum)
                  count
                  average: amount(calculate: average)
                  receivers: receiver {
                    address
                    annotation
                  }
                  senders: sender {
                    address  
                    annotation
                  }
                }
              }
            }
            """
            
            # Параметры запроса
            variables = {
                "currency": currency,
                "from": (datetime.now() - timedelta(hours=self.timeframe_hours)).isoformat(),
                "till": datetime.now().isoformat()
            }
            
            response = self._execute_query(query, variables)
            
            if not response or 'data' not in response:
                return 0
                
            transfers = response['data']['ethereum']['transfers']
            
            # Анализируем направления потоков
            inflow_score = 0
            outflow_score = 0
            
            for transfer in transfers:
                amount = float(transfer.get('sum', 0))
                receivers = transfer.get('receivers', [])
                senders = transfer.get('senders', [])
                
                # Определяем тип адресов (биржи, киты, DeFi)
                receiver_type = self._classify_address_type(receivers)
                sender_type = self._classify_address_type(senders)
                
                # Логика определения inflow/outflow
                if receiver_type == 'exchange' and sender_type == 'whale':
                    outflow_score += amount  # Киты продают на биржах
                elif receiver_type == 'whale' and sender_type == 'exchange':
                    inflow_score += amount  # Киты покупают с бирж
                elif receiver_type == 'defi':
                    inflow_score += amount * 0.5  # Блокировка в DeFi
                elif sender_type == 'defi':
                    outflow_score += amount * 0.5  # Разблокировка из DeFi
            
            # Вычисляем сигнал
            total_flow = inflow_score + outflow_score
            if total_flow > self.large_flow_threshold:
                signal = (inflow_score - outflow_score) / total_flow
                return max(-1, min(1, signal))
            
            return 0
            
        except Exception as e:
            logging.error(f"Ошибка анализа inflow/outflow для {currency}: {e}")
            return 0

    def _analyze_dex_activity(self, currency: str) -> float:
        """
        Анализирует активность на децентрализованных биржах
        
        Args:
            currency: Базовая валюта
            
        Returns:
            float: Сигнал от -1 до 1
        """
        try:
            query = """
            query ($currency: String!, $from: ISO8601DateTime!, $till: ISO8601DateTime!) {
              ethereum(network: ethereum) {
                dexTrades(
                  baseCurrency: {symbol: {is: $currency}}
                  date: {between: [$from, $till]}
                  tradeAmountUsd: {gt: 10000}
                ) {
                  buys: trades(side: {is: BUY}) {
                    count
                    volume: tradeAmount(calculate: sum)
                    volumeUsd: tradeAmount(in: USD, calculate: sum)
                  }
                  sells: trades(side: {is: SELL}) {
                    count  
                    volume: tradeAmount(calculate: sum)
                    volumeUsd: tradeAmount(in: USD, calculate: sum)
                  }
                }
              }
            }
            """
            
            variables = {
                "currency": currency,
                "from": (datetime.now() - timedelta(hours=self.timeframe_hours)).isoformat(),
                "till": datetime.now().isoformat()
            }
            
            response = self._execute_query(query, variables)
            
            if not response or 'data' not in response:
                return 0
                
            dex_data = response['data']['ethereum']['dexTrades']
            
            buy_volume = sum(float(trade.get('volumeUsd', 0)) for trade in dex_data.get('buys', []))
            sell_volume = sum(float(trade.get('volumeUsd', 0)) for trade in dex_data.get('sells', []))
            
            total_volume = buy_volume + sell_volume
            
            if total_volume > self.dex_volume_threshold:
                signal = (buy_volume - sell_volume) / total_volume
                return max(-1, min(1, signal * 1.2))  # Усиливаем DEX сигнал
            
            return 0
            
        except Exception as e:
            logging.error(f"Ошибка анализа DEX активности для {currency}: {e}")
            return 0

    def _analyze_whale_accumulation(self, currency: str) -> float:
        """
        Анализирует накопление/распределение китами
        
        Args:
            currency: Базовая валюта
            
        Returns:
            float: Сигнал от -1 до 1
        """
        try:
            query = """
            query ($currency: String!, $from: ISO8601DateTime!, $till: ISO8601DateTime!) {
              ethereum(network: ethereum) {
                transfers(
                  currency: {symbol: {is: $currency}}
                  date: {between: [$from, $till]}
                  amount: {gt: 1000}
                ) {
                  senders: sender {
                    address
                    balance: balance(currency: {symbol: $currency})
                  }
                  receivers: receiver {
                    address
                    balance: balance(currency: {symbol: $currency})
                  }
                  amount
                  count
                }
              }
            }
            """
            
            variables = {
                "currency": currency,
                "from": (datetime.now() - timedelta(hours=self.timeframe_hours)).isoformat(),
                "till": datetime.now().isoformat()
            }
            
            response = self._execute_query(query, variables)
            
            if not response or 'data' not in response:
                return 0
                
            transfers = response['data']['ethereum']['transfers']
            
            accumulation_score = 0
            distribution_score = 0
            
            for transfer in transfers:
                amount = float(transfer.get('amount', 0))
                
                # Анализируем балансы отправителей и получателей
                senders = transfer.get('senders', [])
                receivers = transfer.get('receivers', [])
                
                for sender in senders:
                    balance = float(sender.get('balance', 0))
                    if balance > 10000:  # Кит
                        distribution_score += amount
                        
                for receiver in receivers:
                    balance = float(receiver.get('balance', 0))
                    if balance > 10000:  # Кит
                        accumulation_score += amount
            
            # Вычисляем сигнал
            total_activity = accumulation_score + distribution_score
            if total_activity > 0:
                signal = (accumulation_score - distribution_score) / total_activity
                return max(-1, min(1, signal))
            
            return 0
            
        except Exception as e:
            logging.error(f"Ошибка анализа накопления китами для {currency}: {e}")
            return 0

    def _analyze_exchange_flows(self, currency: str) -> float:
        """
        Анализирует потоки на/с бирж
        
        Args:
            currency: Базовая валюта
            
        Returns:
            float: Сигнал от -1 до 1
        """
        try:
            # Список известных биржевых адресов
            exchange_addresses = self._get_exchange_addresses()
            
            query = """
            query ($currency: String!, $addresses: [String!]!, $from: ISO8601DateTime!, $till: ISO8601DateTime!) {
              ethereum(network: ethereum) {
                transfers(
                  currency: {symbol: {is: $currency}}
                  date: {between: [$from, $till]}
                  any: [
                    {sender: {in: $addresses}},
                    {receiver: {in: $addresses}}
                  ]
                  amount: {gt: 100}
                ) {
                  inflows: transfers(receiver: {in: $addresses}) {
                    amount(calculate: sum)
                    count
                  }
                  outflows: transfers(sender: {in: $addresses}) {
                    amount(calculate: sum) 
                    count
                  }
                }
              }
            }
            """
            
            variables = {
                "currency": currency,
                "addresses": exchange_addresses,
                "from": (datetime.now() - timedelta(hours=self.timeframe_hours)).isoformat(),
                "till": datetime.now().isoformat()
            }
            
            response = self._execute_query(query, variables)
            
            if not response or 'data' not in response:
                return 0
                
            flows = response['data']['ethereum']['transfers']
            
            inflow_amount = sum(float(flow.get('amount', 0)) for flow in flows.get('inflows', []))
            outflow_amount = sum(float(flow.get('amount', 0)) for flow in flows.get('outflows', []))
            
            total_flow = inflow_amount + outflow_amount
            
            if total_flow > self.large_flow_threshold:
                # Outflow с бирж = бычий сигнал (накопление в кошельках)
                # Inflow на биржи = медвежий сигнал (продажи)
                signal = (outflow_amount - inflow_amount) / total_flow
                return max(-1, min(1, signal))
            
            return 0
            
        except Exception as e:
            logging.error(f"Ошибка анализа биржевых потоков для {currency}: {e}")
            return 0

    def _execute_query(self, query: str, variables: dict) -> Optional[dict]:
        """
        Выполняет GraphQL запрос к Bitquery
        
        Args:
            query: GraphQL запрос
            variables: Переменные запроса
            
        Returns:
            Optional[dict]: Ответ от API
        """
        try:
            payload = {
                "query": query,
                "variables": variables
            }
            
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'errors' in data:
                logging.error(f"Ошибки в GraphQL запросе: {data['errors']}")
                return None
                
            return data
            
        except Exception as e:
            logging.error(f"Ошибка выполнения Bitquery запроса: {e}")
            return None

    def _classify_address_type(self, addresses: List[dict]) -> str:
        """
        Классифицирует тип адресов
        
        Args:
            addresses: Список адресов
            
        Returns:
            str: Тип адреса ('exchange', 'whale', 'defi', 'regular')
        """
        try:
            exchange_addresses = self._get_exchange_addresses()
            defi_addresses = self._get_defi_addresses()
            
            for addr_info in addresses:
                address = addr_info.get('address', '')
                annotation = addr_info.get('annotation', '')
                
                if address in exchange_addresses or 'exchange' in annotation.lower():
                    return 'exchange'
                elif address in defi_addresses or any(protocol in annotation.lower() 
                                                   for protocol in ['uniswap', 'compound', 'aave', 'curve']):
                    return 'defi'
                elif 'whale' in annotation.lower():
                    return 'whale'
            
            return 'regular'
            
        except Exception:
            return 'regular'

    def _get_exchange_addresses(self) -> List[str]:
        """
        Возвращает список известных адресов бирж
        
        Returns:
            List[str]: Адреса бирж
        """
        return [
            "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",  # Binance
            "0xd551234ae421e3bcba99a0da6d736074f22192ff",  # Binance
            "0x564286362092d8e7936f0549571a803b203aaced",  # Binance
            "0x0681d8db095565fe8a346fa0277bffde9c0edbbf",  # Binance
            "0xfe9e8709d3215310075d67e3ed32a380ccf451c8",  # Coinbase
            "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",  # Coinbase
            "0x77696bb39917c91a0c3908d577d5e322095425ca",  # Coinbase
            "0x503828976d22510aad0201ac7ec88293211d23da",  # Coinbase
            "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Kraken
            "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13",  # Kraken
            "0xe853c56864a2ebe4576a807d26fdc4a0ada51919",  # Kraken
        ]

    def _get_defi_addresses(self) -> List[str]:
        """
        Возвращает список известных DeFi контрактов
        
        Returns:
            List[str]: Адреса DeFi протоколов
        """
        return [
            "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9",  # Aave
            "0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b",  # Compound
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",  # Uniswap
            "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",  # AAVE Token
        ]

    def get_detailed_analysis(self, trading_pair: str) -> Dict:
        """
        Возвращает детальный анализ для заданной пары
        
        Args:
            trading_pair: Торговая пара
            
        Returns:
            Dict: Подробная информация об анализе
        """
        try:
            base_currency = self._extract_base_currency(trading_pair)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "trading_pair": trading_pair,
                "base_currency": base_currency,
                "inflow_outflow": self._analyze_inflow_outflow(base_currency),
                "dex_activity": self._analyze_dex_activity(base_currency),
                "whale_accumulation": self._analyze_whale_accumulation(base_currency),
                "exchange_flows": self._analyze_exchange_flows(base_currency),
                "timeframe_hours": self.timeframe_hours
            }
        except Exception as e:
            logging.error(f"Ошибка детального анализа Bitquery для {trading_pair}: {e}")
            return {}