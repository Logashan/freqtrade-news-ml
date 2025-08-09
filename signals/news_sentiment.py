"""
Модуль для анализа новостного сентимента криптовалют
Использует различные API для получения новостей и анализа настроений

Автор: Trading Bot
Версия: 1.0
"""

import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import json
from textblob import TextBlob
import re


class NewsSentimentAnalyzer:
    """
    Анализатор новостного сентимента для криптовалют
    Анализирует новости из различных источников и определяет настроения
    """
    
    def __init__(self, api_key: str = None):
        """
        Инициализация анализатора новостного сентимента
        
        Args:
            api_key: API ключ для новостных сервисов
        """
        self.api_key = api_key
        self.session = requests.Session()
        
        # Настройки для анализа
        self.timeframe_hours = 24  # Анализируем новости за последние 24 часа
        self.min_confidence = 0.6  # Минимальная уверенность в сентименте
        self.weight_recent = 0.7   # Вес недавних новостей
        
        # Кэширование
        self.cache = {}
        self.cache_ttl = 1800  # 30 минут
        
        # Источники новостей
        self.news_sources = [
            "cointelegraph.com",
            "coindesk.com", 
            "bitcoin.com",
            "decrypt.co",
            "theblock.co"
        ]
        
        logging.info("News Sentiment Analyzer инициализирован")

    def get_sentiment_signal(self, trading_pair: str) -> int:
        """
        Получает сигнал на основе новостного сентимента
        
        Args:
            trading_pair: Торговая пара (например, "BTC/USDT:USDT")
            
        Returns:
            int: 1 = позитивный, 0 = нейтральный, -1 = негативный
        """
        try:
            # Извлекаем базовую валюту
            base_currency = self._extract_base_currency(trading_pair)
            
            # Проверяем кэш
            cache_key = f"news_sentiment_{base_currency}_{int(time.time() // self.cache_ttl)}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Получаем новости и анализируем сентимент
            news_data = self._get_recent_news(base_currency)
            sentiment_score = self._analyze_sentiment(news_data)
            
            # Преобразуем в дискретный сигнал
            if sentiment_score > 0.3:
                signal = 1  # Позитивный
            elif sentiment_score < -0.3:
                signal = -1  # Негативный
            else:
                signal = 0  # Нейтральный
                
            # Кэшируем результат
            self.cache[cache_key] = signal
            
            logging.info(f"Новостной сентимент для {base_currency}: {signal} (оценка: {sentiment_score:.2f})")
            return signal
            
        except Exception as e:
            logging.error(f"Ошибка анализа новостного сентимента: {e}")
            return 0

    def _extract_base_currency(self, trading_pair: str) -> str:
        """Извлекает базовую валюту из торговой пары"""
        return trading_pair.split('/')[0].split(':')[0]

    def _get_recent_news(self, currency: str) -> List[Dict]:
        """
        Получает недавние новости для заданной валюты
        
        Args:
            currency: Криптовалюта (BTC, ETH, SOL и т.д.)
            
        Returns:
            List[Dict]: Список новостей с заголовками и текстом
        """
        try:
            # Используем NewsAPI или альтернативный источник
            if self.api_key:
                return self._get_news_from_api(currency)
            else:
                return self._get_news_from_rss(currency)
                
        except Exception as e:
            logging.error(f"Ошибка получения новостей: {e}")
            return []

    def _get_news_from_api(self, currency: str) -> List[Dict]:
        """Получает новости через NewsAPI"""
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": f"{currency} cryptocurrency",
                "from": (datetime.now() - timedelta(hours=self.timeframe_hours)).isoformat(),
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": self.api_key
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("articles", [])
            
        except Exception as e:
            logging.error(f"Ошибка NewsAPI: {e}")
            return []

    def _get_news_from_rss(self, currency: str) -> List[Dict]:
        """Получает новости через RSS фиды (fallback)"""
        # Здесь можно добавить парсинг RSS фидов
        # Пока возвращаем пустой список
        return []

    def _analyze_sentiment(self, news_data: List[Dict]) -> float:
        """
        Анализирует сентимент новостей
        
        Args:
            news_data: Список новостей
            
        Returns:
            float: Оценка сентимента от -1 до 1
        """
        if not news_data:
            return 0.0
            
        total_sentiment = 0.0
        total_weight = 0.0
        
        for i, article in enumerate(news_data):
            # Анализируем заголовок и описание
            title = article.get("title", "")
            description = article.get("description", "")
            content = f"{title} {description}"
            
            # Очищаем текст
            clean_content = self._clean_text(content)
            
            # Анализируем сентимент
            blob = TextBlob(clean_content)
            sentiment = blob.sentiment.polarity
            
            # Взвешиваем по времени (более новые новости имеют больший вес)
            weight = self.weight_recent ** i
            
            total_sentiment += sentiment * weight
            total_weight += weight
            
        if total_weight > 0:
            return total_sentiment / total_weight
        else:
            return 0.0

    def _clean_text(self, text: str) -> str:
        """Очищает текст от HTML тегов и специальных символов"""
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        # Удаляем специальные символы
        text = re.sub(r'[^\w\s]', '', text)
        # Приводим к нижнему регистру
        return text.lower()

    def get_detailed_sentiment_analysis(self, trading_pair: str) -> Dict:
        """
        Получает детальный анализ сентимента
        
        Args:
            trading_pair: Торговая пара
            
        Returns:
            Dict: Детальная информация о сентименте
        """
        try:
            base_currency = self._extract_base_currency(trading_pair)
            news_data = self._get_recent_news(base_currency)
            
            analysis = {
                "currency": base_currency,
                "total_articles": len(news_data),
                "sentiment_score": self._analyze_sentiment(news_data),
                "recent_articles": news_data[:5],  # Последние 5 статей
                "timestamp": datetime.now().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            logging.error(f"Ошибка детального анализа: {e}")
            return {}