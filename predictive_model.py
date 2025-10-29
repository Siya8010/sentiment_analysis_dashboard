"""
Predictive Model Module
Uses LSTM neural networks and Prophet for time series forecasting
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging

# Deep Learning
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

# Prophet for time series
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except Exception:
    Prophet = None
    PROPHET_AVAILABLE = False

# Scikit-learn for preprocessing
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentimentDataset(Dataset):
    """Custom dataset for LSTM training"""
    
    def __init__(self, sequences, targets):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class LSTMModel(nn.Module):
    """LSTM Neural Network for sentiment prediction"""
    
    def __init__(self, input_size=3, hidden_size=64, num_layers=2, dropout=0.2):
        super(LSTMModel, self).__init__()
        
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 3)  # Output: [positive, negative, neutral]
        )
    
    def forward(self, x):
        # LSTM forward pass
        lstm_out, _ = self.lstm(x)
        
        # Take the last output
        last_output = lstm_out[:, -1, :]
        
        # Fully connected layers
        output = self.fc(last_output)
        
        return output


class PredictiveModel:
    """Main predictive model combining LSTM and Prophet"""
    
    def __init__(self, sequence_length=14):
        """
        Initialize predictive model
        
        Args:
            sequence_length: Number of days to look back for predictions
        """
        self.sequence_length = sequence_length
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize LSTM model
        self.lstm_model = LSTMModel().to(self.device)
        self.lstm_model.eval()
        
        # Scalers for normalization
        self.scaler = MinMaxScaler()
        
        # Prophet models for each sentiment
        self.prophet_positive = None
        self.prophet_negative = None
        self.prophet_neutral = None
        
        # Performance metrics
        self.last_mae = 0.0
        self.last_rmse = 0.0
        self.confidence_threshold = 0.7
        
        logger.info(f"Predictive model initialized on {self.device}")
    
    
    def prepare_sequences(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare sequences for LSTM training/prediction
        
        Args:
            data: DataFrame with sentiment scores
            
        Returns:
            Tuple of (sequences, targets)
        """
        # Extract sentiment columns
        sentiment_data = data[['positive', 'negative', 'neutral']].values
        
        # Normalize data
        scaled_data = self.scaler.fit_transform(sentiment_data)
        
        sequences = []
        targets = []
        
        for i in range(len(scaled_data) - self.sequence_length):
            seq = scaled_data[i:i + self.sequence_length]
            target = scaled_data[i + self.sequence_length]
            
            sequences.append(seq)
            targets.append(target)
        
        return np.array(sequences), np.array(targets)
    
    
    def train_lstm(self, historical_data: List[Dict], epochs=50, batch_size=32):
        """
        Train LSTM model on historical data
        
        Args:
            historical_data: List of historical sentiment records
            epochs: Number of training epochs
            batch_size: Training batch size
        """
        logger.info(f"Training LSTM model with {len(historical_data)} samples")
        
        # Convert to DataFrame
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Prepare sequences
        sequences, targets = self.prepare_sequences(df)
        
        # Create dataset and dataloader
        dataset = SentimentDataset(sequences, targets)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Training setup
        self.lstm_model.train()
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.lstm_model.parameters(), lr=0.001)
        
        # Training loop
        for epoch in range(epochs):
            total_loss = 0
            
            for batch_seq, batch_target in dataloader:
                batch_seq = batch_seq.to(self.device)
                batch_target = batch_target.to(self.device)
                
                # Forward pass
                outputs = self.lstm_model(batch_seq)
                loss = criterion(outputs, batch_target)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            if (epoch + 1) % 10 == 0:
                avg_loss = total_loss / len(dataloader)
                logger.info(f"Epoch [{epoch+1}/{epochs}], Loss: {avg_loss:.4f}")
        
        self.lstm_model.eval()
        logger.info("LSTM training completed")
    
    
    def train_prophet(self, historical_data: List[Dict]):
        """
        Train Prophet models on historical data
        
        Args:
            historical_data: List of historical sentiment records
        """
        if not PROPHET_AVAILABLE:
            logger.warning("Prophet not available. Skipping Prophet training.")
            return
        logger.info("Training Prophet models")
        
        # Convert to DataFrame
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Train separate Prophet models for each sentiment
        for sentiment_type in ['positive', 'negative', 'neutral']:
            prophet_df = pd.DataFrame({
                'ds': df['date'],
                'y': df[sentiment_type]
            })
            
            model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
                changepoint_prior_scale=0.05
            )
            
            model.fit(prophet_df)
            
            if sentiment_type == 'positive':
                self.prophet_positive = model
            elif sentiment_type == 'negative':
                self.prophet_negative = model
            else:
                self.prophet_neutral = model
        
        logger.info("Prophet training completed")
    
    
    def predict_lstm(self, recent_data: pd.DataFrame, forecast_days: int) -> pd.DataFrame:
        """
        Make predictions using LSTM model
        
        Args:
            recent_data: Recent sentiment data
            forecast_days: Number of days to forecast
            
        Returns:
            DataFrame with predictions
        """
        # Prepare last sequence
        sentiment_data = recent_data[['positive', 'negative', 'neutral']].values
        scaled_data = self.scaler.transform(sentiment_data)
        
        predictions = []
        current_sequence = scaled_data[-self.sequence_length:]
        
        with torch.no_grad():
            for _ in range(forecast_days):
                # Prepare input
                input_seq = torch.FloatTensor(current_sequence).unsqueeze(0).to(self.device)
                
                # Predict
                prediction = self.lstm_model(input_seq)
                pred_np = prediction.cpu().numpy()[0]
                
                predictions.append(pred_np)
                
                # Update sequence
                current_sequence = np.vstack([current_sequence[1:], pred_np])
        
        # Inverse transform predictions
        predictions = self.scaler.inverse_transform(np.array(predictions))
        
        # Create DataFrame
        last_date = recent_data['date'].max()
        future_dates = [last_date + timedelta(days=i+1) for i in range(forecast_days)]
        
        pred_df = pd.DataFrame({
            'date': future_dates,
            'positive': predictions[:, 0],
            'negative': predictions[:, 1],
            'neutral': predictions[:, 2],
            'model': 'LSTM'
        })
        
        return pred_df
    
    
    def predict_prophet(self, forecast_days: int) -> pd.DataFrame:
        """
        Make predictions using Prophet models
        
        Args:
            forecast_days: Number of days to forecast
            
        Returns:
            DataFrame with predictions
        """
        if not PROPHET_AVAILABLE or not all([self.prophet_positive, self.prophet_negative, self.prophet_neutral]):
            raise ValueError("Prophet unavailable or models not trained")
        
        # Create future dataframe
        future = self.prophet_positive.make_future_dataframe(periods=forecast_days)
        
        # Predict for each sentiment
        pred_positive = self.prophet_positive.predict(future)
        pred_negative = self.prophet_negative.predict(future)
        pred_neutral = self.prophet_neutral.predict(future)
        
        # Combine predictions (take only future dates)
        pred_df = pd.DataFrame({
            'date': pred_positive['ds'].tail(forecast_days),
            'positive': pred_positive['yhat'].tail(forecast_days).values,
            'negative': pred_negative['yhat'].tail(forecast_days).values,
            'neutral': pred_neutral['yhat'].tail(forecast_days).values,
            'positive_lower': pred_positive['yhat_lower'].tail(forecast_days).values,
            'positive_upper': pred_positive['yhat_upper'].tail(forecast_days).values,
            'model': 'Prophet'
        })
        
        # Ensure predictions are within valid range [0, 100]
        for col in ['positive', 'negative', 'neutral']:
            pred_df[col] = pred_df[col].clip(0, 100)
        
        return pred_df
    
    
    def predict(self, historical_data: List[Dict], forecast_days: int = 7) -> Dict:
        """
        Generate ensemble predictions combining LSTM and Prophet
        
        Args:
            historical_data: Historical sentiment data
            forecast_days: Number of days to forecast
            
        Returns:
            Dictionary with predictions and metadata
        """
        logger.info(f"Generating {forecast_days}-day forecast")
        
        # Convert to DataFrame
        df = pd.DataFrame(historical_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Ensure we have enough data
        if len(df) < self.sequence_length + 7:
            return {
                'error': f'Insufficient data. Need at least {self.sequence_length + 7} days',
                'predictions': []
            }
        
        try:
            # Train models if needed
            if not hasattr(self, 'models_trained'):
                self.train_prophet(historical_data)
                self.models_trained = True
            
            # Get predictions from both models
            lstm_pred = self.predict_lstm(df, forecast_days)
            prophet_pred = None
            if PROPHET_AVAILABLE:
                try:
                    prophet_pred = self.predict_prophet(forecast_days)
                except Exception as e:
                    logger.warning(f"Prophet prediction unavailable: {e}")
            
            # Ensemble: weighted average (70% LSTM, 30% Prophet)
            predictions = []
            
            for i in range(forecast_days):
                date = lstm_pred.iloc[i]['date']
                
                # Ensemble predictions
                if prophet_pred is not None:
                    positive = 0.7 * lstm_pred.iloc[i]['positive'] + 0.3 * prophet_pred.iloc[i]['positive']
                    negative = 0.7 * lstm_pred.iloc[i]['negative'] + 0.3 * prophet_pred.iloc[i]['negative']
                    neutral = 0.7 * lstm_pred.iloc[i]['neutral'] + 0.3 * prophet_pred.iloc[i]['neutral']
                else:
                    positive = lstm_pred.iloc[i]['positive']
                    negative = lstm_pred.iloc[i]['negative']
                    neutral = lstm_pred.iloc[i]['neutral']
                
                # Normalize to sum to 100
                total = positive + negative + neutral
                positive = (positive / total) * 100
                negative = (negative / total) * 100
                neutral = (neutral / total) * 100
                
                # Calculate confidence (decreases with forecast horizon)
                confidence = max(0.5, 0.9 - (i * 0.05))
                
                # Confidence intervals from Prophet
                if prophet_pred is not None:
                    upper_bound = prophet_pred.iloc[i]['positive_upper']
                    lower_bound = prophet_pred.iloc[i]['positive_lower']
                else:
                    # naive bounds: +/- 5%
                    upper_bound = min(100.0, positive + 5)
                    lower_bound = max(0.0, positive - 5)
                
                predictions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'positive_score': round(positive, 2),
                    'negative_score': round(negative, 2),
                    'neutral_score': round(neutral, 2),
                    'confidence': round(confidence, 2),
                    'upper_bound': round(upper_bound, 2),
                    'lower_bound': round(lower_bound, 2),
                    'dominant_sentiment': max(
                        [('positive', positive), ('negative', negative), ('neutral', neutral)],
                        key=lambda x: x[1]
                    )[0]
                })
            
            # Calculate overall trend
            avg_positive = np.mean([p['positive_score'] for p in predictions])
            avg_negative = np.mean([p['negative_score'] for p in predictions])
            
            trend = 'improving' if avg_positive > 65 else 'declining' if avg_negative > 30 else 'stable'
            
            return {
                'predictions': predictions,
                'forecast_days': forecast_days,
                'trend': trend,
                'avg_confidence': round(np.mean([p['confidence'] for p in predictions]), 2),
                'model_info': {
                    'primary': 'LSTM',
                    'fallback': 'Prophet' if PROPHET_AVAILABLE else 'None',
                    'ensemble_weight': '70-30' if PROPHET_AVAILABLE else '100-0'
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return {
                'error': str(e),
                'predictions': []
            }
    
    
    def get_latest_predictions(self) -> List[Dict]:
        """Get the most recent predictions (mock for example)"""
        # This would typically fetch from cache or database
        return []
    
    
    def detect_anomalies(self, recent_data: pd.DataFrame) -> List[Dict]:
        """
        Detect anomalies in sentiment patterns
        
        Args:
            recent_data: Recent sentiment data
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Calculate rolling statistics
        window = 7
        for col in ['positive', 'negative', 'neutral']:
            rolling_mean = recent_data[col].rolling(window=window).mean()
            rolling_std = recent_data[col].rolling(window=window).std()
            
            # Detect points outside 2 standard deviations
            threshold = 2
            for idx in range(window, len(recent_data)):
                value = recent_data.iloc[idx][col]
                mean = rolling_mean.iloc[idx]
                std = rolling_std.iloc[idx]
                
                if abs(value - mean) > threshold * std:
                    anomalies.append({
                        'date': recent_data.iloc[idx]['date'].strftime('%Y-%m-%d'),
                        'type': col,
                        'value': round(value, 2),
                        'expected': round(mean, 2),
                        'deviation': round(abs(value - mean) / std, 2),
                        'severity': 'high' if abs(value - mean) > 3 * std else 'medium'
                    })
        
        return anomalies


# Example usage and testing
if __name__ == "__main__":
    # Generate sample historical data
    dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
    
    historical_data = []
    for i, date in enumerate(dates):
        # Simulate sentiment trends with some noise
        base_positive = 70 + 10 * np.sin(i / 10) + np.random.randn() * 5
        base_negative = 20 + 5 * np.sin(i / 15) + np.random.randn() * 3
        base_neutral = 10 + np.random.randn() * 2
        
        # Normalize
        total = base_positive + base_negative + base_neutral
        
        historical_data.append({
            'date': date,
            'positive': (base_positive / total) * 100,
            'negative': (base_negative / total) * 100,
            'neutral': (base_neutral / total) * 100,
            'total_mentions': np.random.randint(800, 1500)
        })
    
    # Initialize and test model
    model = PredictiveModel()
    
    print("=== Generating Predictions ===")
    predictions = model.predict(historical_data, forecast_days=7)
    
    if 'error' not in predictions:
        print(f"\nTrend: {predictions['trend']}")
        print(f"Average Confidence: {predictions['avg_confidence']}")
        print("\nPredictions:")
        for pred in predictions['predictions']:
            print(f"\n{pred['date']}:")
            print(f"  Positive: {pred['positive_score']}%")
            print(f"  Negative: {pred['negative_score']}%")
            print(f"  Neutral: {pred['neutral_score']}%")
            print(f"  Confidence: {pred['confidence']}")
            print(f"  Dominant: {pred['dominant_sentiment']}")
    else:
        print(f"Error: {predictions['error']}")
    
    print("\n=== Detecting Anomalies ===")
    df = pd.DataFrame(historical_data)
    anomalies = model.detect_anomalies(df)
    print(f"Found {len(anomalies)} anomalies")
    for anomaly in anomalies[:5]:  # Show first 5
        print(f"\n{anomaly['date']} - {anomaly['type']}:")
        print(f"  Value: {anomaly['value']}, Expected: {anomaly['expected']}")
        print(f"  Severity: {anomaly['severity']}")