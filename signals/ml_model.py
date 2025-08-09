"""
Модуль для машинного обучения в торговой стратегии
Использует различные ML модели для предсказания движений цены

Автор: Trading Bot
Версия: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
import logging
import pickle
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib


class MLModel:
    """
    Модель машинного обучения для предсказания торговых сигналов
    Использует ансамбль классификаторов для предсказания направления цены
    """
    
    def __init__(self, model_path: str = None):
        """
        Инициализация ML модели
        
        Args:
            model_path: Путь к сохранённой модели
        """
        self.model_path = model_path or "user_data/freqaimodels/ml_model.pkl"
        self.scaler_path = "user_data/freqaimodels/scaler.pkl"
        
        # Параметры модели
        self.lookback_periods = 20  # Количество периодов для анализа
        self.prediction_threshold = 0.6  # Порог уверенности для сигнала
        self.retrain_interval_hours = 24  # Интервал переобучения
        
        # Модели
        self.rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.gb_model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42
        )
        
        # Скалер для нормализации данных
        self.scaler = StandardScaler()
        
        # Статус модели
        self.is_trained = False
        self.last_training = None
        
        # Загружаем модель если существует
        self._load_model()
        
        logging.info("ML Model инициализирован")

    def _load_model(self):
        """Загружает сохранённую модель"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.rf_model = model_data['rf_model']
                    self.gb_model = model_data['gb_model']
                    self.is_trained = True
                    self.last_training = model_data.get('last_training')
                    
                if os.path.exists(self.scaler_path):
                    with open(self.scaler_path, 'rb') as f:
                        self.scaler = pickle.load(f)
                        
                logging.info("ML модель загружена успешно")
            else:
                logging.info("ML модель не найдена, будет создана новая")
                
        except Exception as e:
            logging.error(f"Ошибка загрузки ML модели: {e}")

    def _save_model(self):
        """Сохраняет модель"""
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            model_data = {
                'rf_model': self.rf_model,
                'gb_model': self.gb_model,
                'last_training': datetime.now()
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
                
            logging.info("ML модель сохранена")
            
        except Exception as e:
            logging.error(f"Ошибка сохранения ML модели: {e}")

    def prepare_features(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Подготавливает признаки для ML модели
        
        Args:
            dataframe: DataFrame с техническими индикаторами
            
        Returns:
            pd.DataFrame: DataFrame с подготовленными признаками
        """
        try:
            df = dataframe.copy()
            
            # Базовые технические индикаторы
            features = [
                'rsi', 'rsi_1h', 'macd', 'macdsignal', 'macdhist',
                'bb_lowerband', 'bb_middleband', 'bb_upperband',
                'volume', 'close', 'high', 'low', 'open'
            ]
            
            # Добавляем производные признаки
            df['price_change'] = df['close'].pct_change()
            df['volume_change'] = df['volume'].pct_change()
            df['high_low_ratio'] = df['high'] / df['low']
            df['close_open_ratio'] = df['close'] / df['open']
            
            # Добавляем лаговые признаки
            for lag in [1, 2, 3, 5, 10]:
                df[f'price_lag_{lag}'] = df['close'].shift(lag)
                df[f'volume_lag_{lag}'] = df['volume'].shift(lag)
                df[f'rsi_lag_{lag}'] = df['rsi'].shift(lag)
                
            # Добавляем скользящие средние
            for window in [5, 10, 20]:
                df[f'sma_{window}'] = df['close'].rolling(window=window).mean()
                df[f'volume_sma_{window}'] = df['volume'].rolling(window=window).mean()
                
            # Добавляем волатильность
            df['volatility'] = df['close'].rolling(window=20).std()
            
            # Удаляем NaN значения
            df = df.dropna()
            
            return df
            
        except Exception as e:
            logging.error(f"Ошибка подготовки признаков: {e}")
            return pd.DataFrame()

    def prepare_target(self, dataframe: pd.DataFrame, forward_periods: int = 5) -> pd.Series:
        """
        Подготавливает целевую переменную
        
        Args:
            dataframe: DataFrame с данными
            forward_periods: Количество периодов вперёд для предсказания
            
        Returns:
            pd.Series: Целевая переменная (1 = рост, 0 = падение)
        """
        try:
            # Вычисляем будущее изменение цены
            future_returns = dataframe['close'].shift(-forward_periods) / dataframe['close'] - 1
            
            # Создаём бинарную целевую переменную
            target = (future_returns > 0).astype(int)
            
            return target
            
        except Exception as e:
            logging.error(f"Ошибка подготовки целевой переменной: {e}")
            return pd.Series()

    def train(self, dataframe: pd.DataFrame) -> bool:
        """
        Обучает модель на исторических данных
        
        Args:
            dataframe: DataFrame с историческими данными
            
        Returns:
            bool: True если обучение прошло успешно
        """
        try:
            logging.info("Начинаем обучение ML модели...")
            
            # Подготавливаем данные
            df_features = self.prepare_features(dataframe)
            if df_features.empty:
                logging.error("Не удалось подготовить признаки")
                return False
                
            target = self.prepare_target(df_features)
            if target.empty:
                logging.error("Не удалось подготовить целевую переменную")
                return False
                
            # Убираем строки где нет целевой переменной
            df_features = df_features.iloc[:-5]  # Убираем последние 5 строк
            target = target.iloc[:-5]
            
            # Выбираем числовые колонки
            numeric_columns = df_features.select_dtypes(include=[np.number]).columns
            X = df_features[numeric_columns]
            y = target
            
            # Удаляем строки с NaN
            mask = ~(X.isna().any(axis=1) | y.isna())
            X = X[mask]
            y = y[mask]
            
            if len(X) < 100:
                logging.error("Недостаточно данных для обучения")
                return False
                
            # Разделяем на обучающую и тестовую выборки
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Нормализуем данные
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Обучаем модели
            self.rf_model.fit(X_train_scaled, y_train)
            self.gb_model.fit(X_train_scaled, y_train)
            
            # Оцениваем качество
            rf_pred = self.rf_model.predict(X_test_scaled)
            gb_pred = self.gb_model.predict(X_test_scaled)
            
            rf_accuracy = accuracy_score(y_test, rf_pred)
            gb_accuracy = accuracy_score(y_test, gb_pred)
            
            logging.info(f"Точность Random Forest: {rf_accuracy:.3f}")
            logging.info(f"Точность Gradient Boosting: {gb_accuracy:.3f}")
            
            # Сохраняем модель
            self.is_trained = True
            self.last_training = datetime.now()
            self._save_model()
            
            logging.info("ML модель обучена и сохранена")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка обучения ML модели: {e}")
            return False

    def predict(self, dataframe: pd.DataFrame) -> Tuple[int, float]:
        """
        Делает предсказание для текущих данных
        
        Args:
            dataframe: DataFrame с текущими данными
            
        Returns:
            Tuple[int, float]: (сигнал, уверенность)
                сигнал: 1 = покупать, 0 = нейтрально, -1 = продавать
                уверенность: от 0 до 1
        """
        try:
            if not self.is_trained:
                logging.warning("ML модель не обучена")
                return 0, 0.0
                
            # Проверяем необходимость переобучения
            if self._should_retrain():
                logging.info("Требуется переобучение модели")
                return 0, 0.0
                
            # Подготавливаем признаки для последней строки
            df_features = self.prepare_features(dataframe)
            if df_features.empty:
                return 0, 0.0
                
            # Берём последнюю строку
            latest_data = df_features.iloc[-1:]
            numeric_columns = latest_data.select_dtypes(include=[np.number]).columns
            X = latest_data[numeric_columns]
            
            # Проверяем на NaN
            if X.isna().any().any():
                logging.warning("NaN значения в данных для предсказания")
                return 0, 0.0
                
            # Нормализуем данные
            X_scaled = self.scaler.transform(X)
            
            # Делаем предсказания
            rf_proba = self.rf_model.predict_proba(X_scaled)[0]
            gb_proba = self.gb_model.predict_proba(X_scaled)[0]
            
            # Комбинируем предсказания (ансамбль)
            combined_proba = (rf_proba + gb_proba) / 2
            
            # Получаем вероятность роста
            prob_up = combined_proba[1]
            prob_down = combined_proba[0]
            
            # Определяем сигнал и уверенность
            if prob_up > self.prediction_threshold:
                signal = 1  # Покупать
                confidence = prob_up
            elif prob_down > self.prediction_threshold:
                signal = -1  # Продавать
                confidence = prob_down
            else:
                signal = 0  # Нейтрально
                confidence = max(prob_up, prob_down)
                
            logging.info(f"ML предсказание: сигнал={signal}, уверенность={confidence:.3f}")
            return signal, confidence
            
        except Exception as e:
            logging.error(f"Ошибка предсказания ML модели: {e}")
            return 0, 0.0

    def _should_retrain(self) -> bool:
        """Проверяет, нужно ли переобучать модель"""
        if not self.last_training:
            return True
            
        hours_since_training = (datetime.now() - self.last_training).total_seconds() / 3600
        return hours_since_training > self.retrain_interval_hours

    def get_model_info(self) -> Dict:
        """
        Возвращает информацию о модели
        
        Returns:
            Dict: Информация о модели
        """
        return {
            "is_trained": self.is_trained,
            "last_training": self.last_training.isoformat() if self.last_training else None,
            "model_path": self.model_path,
            "lookback_periods": self.lookback_periods,
            "prediction_threshold": self.prediction_threshold,
            "retrain_interval_hours": self.retrain_interval_hours
        }
