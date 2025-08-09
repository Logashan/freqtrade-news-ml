"""
Пакет модулей внешних сигналов для торгового бота
Содержит интеграции с внешними API для получения торговых сигналов

Модули:
- helius_signal: Сигналы от Helius API (Solana blockchain)
- bitquery_signal: Сигналы от Bitquery API (on-chain анализ)
- news_sentiment: Анализ новостного сентимента через NewsAPI

Автор: Trading Bot
Версия: 1.0
"""

from .helius_signal import HeliusSignalGenerator
from .bitquery_signal import BitquerySignalGenerator
from .news_sentiment import NewsSentimentAnalyzer

__all__ = [
    'HeliusSignalGenerator',
    'BitquerySignalGenerator', 
    'NewsSentimentAnalyzer'
]

__version__ = "1.0.0"