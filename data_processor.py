"""
Data Processor Module
Handles data transformation, aggregation, and analytics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Process and transform sentiment data"""
    
    def __init__(self):
        """Initialize data processor"""
        logger.info("Data processor initialized")
    
    
    def process_realtime_data(self, raw_data: List[Dict]) -> List[Dict]:
        """
        Process real-time data from social media
        
        Args:
            raw_data: Raw data from social media APIs
            
        Returns:
            Processed and analyzed data
        """
        processed = []
        
        from sentiment_analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        for item in raw_data:
            text = item.get('text', '')
            
            if not text:
                continue
            
            # Analyze sentiment
            sentiment = analyzer.analyze(text)
            
            # Combine with metadata
            processed_item = {
                'id': item.get('id'),
                'text': text[:200],  # Truncate for storage
                'sentiment': sentiment['sentiment'],
                'confidence': sentiment['confidence'],
                'scores': sentiment['scores'],
                'source': item.get('source', 'unknown'),
                'timestamp': item.get('created_at', datetime.utcnow().isoformat()),
                'engagement': item.get('likes', 0) + item.get('retweets', 0) + item.get('replies', 0)
            }
            
            processed.append(processed_item)
        
        return processed
    
    
    def aggregate_historical_data(self, data: List[Dict]) -> Dict:
        """
        Aggregate historical sentiment data
        
        Args:
            data: Historical sentiment records
            
        Returns:
            Aggregated data with insights
        """
        if not data:
            return {'error': 'No data provided'}
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Convert date column if exists
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        # Calculate aggregates
        aggregated = {
            'daily_data': [],
            'summary': {
                'total_mentions': int(df.get('total', df.get('count', pd.Series([0]))).sum()),
                'avg_positive': float(df['positive'].mean()) if 'positive' in df else 0,
                'avg_negative': float(df['negative'].mean()) if 'negative' in df else 0,
                'avg_neutral': float(df['neutral'].mean()) if 'neutral' in df else 0,
                'sentiment_trend': self._calculate_trend(df)
            }
        }
        
        # Group by date
        if 'date' in df.columns:
            for date, group in df.groupby('date'):
                aggregated['daily_data'].append({
                    'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'positive': float(group['positive'].mean()),
                    'negative': float(group['negative'].mean()),
                    'neutral': float(group['neutral'].mean()),
                    'total': int(group.get('total', group.get('count', pd.Series([0]))).sum())
                })
        
        return aggregated
    
    
    def _calculate_trend(self, df: pd.DataFrame) -> str:
        """Calculate overall sentiment trend"""
        if 'positive' not in df.columns or len(df) < 2:
            return 'stable'
        
        # Calculate moving average
        positive_values = df['positive'].values
        
        # Compare first half vs second half
        mid = len(positive_values) // 2
        first_half = np.mean(positive_values[:mid])
        second_half = np.mean(positive_values[mid:])
        
        diff = second_half - first_half
        
        if diff > 5:
            return 'improving'
        elif diff < -5:
            return 'declining'
        else:
            return 'stable'
    
    
    def calculate_trend_insights(self, trends: List[Dict]) -> Dict:
        """
        Calculate insights from trend data
        
        Args:
            trends: Trend data from database
            
        Returns:
            Insights dictionary
        """
        if not trends:
            return {}
        
        df = pd.DataFrame(trends)
        
        insights = {
            'peak_positive_day': None,
            'peak_negative_day': None,
            'most_active_source': None,
            'sentiment_volatility': 0.0,
            'average_confidence': 0.0
        }
        
        # Find peak positive day
        if 'date' in df.columns and 'sentiment' in df.columns:
            positive_df = df[df['sentiment'] == 'positive']
            if not positive_df.empty:
                peak_day = positive_df.groupby('date')['count'].sum().idxmax()
                insights['peak_positive_day'] = str(peak_day)
            
            # Find peak negative day
            negative_df = df[df['sentiment'] == 'negative']
            if not negative_df.empty:
                peak_day = negative_df.groupby('date')['count'].sum().idxmax()
                insights['peak_negative_day'] = str(peak_day)
        
        # Most active source
        if 'source' in df.columns:
            insights['most_active_source'] = df['source'].value_counts().index[0]
        
        # Calculate volatility
        if 'avg_confidence' in df.columns:
            insights['sentiment_volatility'] = float(df['avg_confidence'].std())
            insights['average_confidence'] = float(df['avg_confidence'].mean())
        
        return insights
    
    
    def format_for_crm(self, data: List[Dict]) -> Dict:
        """
        Format data for CRM export (Salesforce format)
        
        Args:
            data: Sentiment data
            
        Returns:
            CRM-formatted data
        """
        if not data:
            return {'records': []}
        
        crm_records = []
        
        for record in data:
            crm_record = {
                'Date__c': record.get('date', datetime.utcnow().strftime('%Y-%m-%d')),
                'Positive_Sentiment__c': record.get('positive', 0),
                'Negative_Sentiment__c': record.get('negative', 0),
                'Neutral_Sentiment__c': record.get('neutral', 0),
                'Total_Mentions__c': record.get('total', 0),
                'Sentiment_Score__c': self._calculate_sentiment_score(record),
                'Status__c': self._get_sentiment_status(record)
            }
            crm_records.append(crm_record)
        
        return {
            'records': crm_records,
            'total_count': len(crm_records),
            'export_date': datetime.utcnow().isoformat()
        }
    
    
    def _calculate_sentiment_score(self, record: Dict) -> float:
        """Calculate overall sentiment score (0-100)"""
        positive = record.get('positive', 0)
        negative = record.get('negative', 0)
        
        # Weighted score: positive contributes positively, negative contributes negatively
        score = (positive - negative + 100) / 2
        return round(score, 2)
    
    
    def _get_sentiment_status(self, record: Dict) -> str:
        """Get sentiment status label"""
        score = self._calculate_sentiment_score(record)
        
        if score >= 70:
            return 'Positive'
        elif score >= 40:
            return 'Neutral'
        else:
            return 'Negative'
    
    
    def detect_sentiment_spikes(self, data: List[Dict], threshold: float = 2.0) -> List[Dict]:
        """
        Detect unusual sentiment spikes
        
        Args:
            data: Historical sentiment data
            threshold: Number of standard deviations for spike detection
            
        Returns:
            List of detected spikes
        """
        if not data or len(data) < 7:
            return []
        
        df = pd.DataFrame(data)
        spikes = []
        
        for column in ['positive', 'negative', 'neutral']:
            if column not in df.columns:
                continue
            
            values = df[column].values
            mean = np.mean(values)
            std = np.std(values)
            
            for i, value in enumerate(values):
                z_score = abs((value - mean) / std) if std > 0 else 0
                
                if z_score > threshold:
                    spikes.append({
                        'date': df.iloc[i].get('date', f'Day {i}'),
                        'type': column,
                        'value': float(value),
                        'expected': float(mean),
                        'z_score': float(z_score),
                        'severity': 'high' if z_score > 3 else 'medium'
                    })
        
        return spikes
    
    
    def calculate_engagement_score(self, data: List[Dict]) -> Dict:
        """
        Calculate engagement metrics
        
        Args:
            data: Social media data with engagement metrics
            
        Returns:
            Engagement analysis
        """
        if not data:
            return {'error': 'No data provided'}
        
        df = pd.DataFrame(data)
        
        engagement = {
            'total_engagement': 0,
            'avg_engagement': 0.0,
            'engagement_by_sentiment': {},
            'engagement_trend': 'stable'
        }
        
        # Calculate total engagement
        if 'engagement' in df.columns:
            engagement['total_engagement'] = int(df['engagement'].sum())
            engagement['avg_engagement'] = float(df['engagement'].mean())
        
        # Engagement by sentiment
        if 'sentiment' in df.columns and 'engagement' in df.columns:
            for sentiment in ['positive', 'negative', 'neutral']:
                sentiment_df = df[df['sentiment'] == sentiment]
                if not sentiment_df.empty:
                    engagement['engagement_by_sentiment'][sentiment] = {
                        'total': int(sentiment_df['engagement'].sum()),
                        'average': float(sentiment_df['engagement'].mean()),
                        'count': len(sentiment_df)
                    }
        
        return engagement
    
    
    def generate_summary_report(self, data: List[Dict]) -> Dict:
        """
        Generate comprehensive summary report
        
        Args:
            data: Historical sentiment data
            
        Returns:
            Summary report
        """
        if not data:
            return {'error': 'No data provided'}
        
        df = pd.DataFrame(data)
        
        report = {
            'period': {
                'start': df['date'].min().strftime('%Y-%m-%d') if 'date' in df.columns else 'N/A',
                'end': df['date'].max().strftime('%Y-%m-%d') if 'date' in df.columns else 'N/A',
                'days': len(df) if 'date' in df.columns else 0
            },
            'sentiment_distribution': {
                'positive': float(df['positive'].mean()) if 'positive' in df else 0,
                'negative': float(df['negative'].mean()) if 'negative' in df else 0,
                'neutral': float(df['neutral'].mean()) if 'neutral' in df else 0
            },
            'volume': {
                'total_mentions': int(df['total'].sum()) if 'total' in df else 0,
                'daily_average': float(df['total'].mean()) if 'total' in df else 0,
                'peak_day': None
            },
            'trends': {
                'overall_trend': self._calculate_trend(df),
                'positive_trend': self._calculate_column_trend(df, 'positive'),
                'negative_trend': self._calculate_column_trend(df, 'negative')
            },
            'key_insights': []
        }
        
        # Find peak day
        if 'date' in df.columns and 'total' in df.columns:
            peak_idx = df['total'].idxmax()
            report['volume']['peak_day'] = df.loc[peak_idx, 'date'].strftime('%Y-%m-%d')
        
        # Generate insights
        report['key_insights'] = self._generate_insights(df)
        
        return report
    
    
    def _calculate_column_trend(self, df: pd.DataFrame, column: str) -> str:
        """Calculate trend for specific column"""
        if column not in df.columns or len(df) < 2:
            return 'stable'
        
        values = df[column].values
        
        # Simple linear regression slope
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 1:
            return 'increasing'
        elif slope < -1:
            return 'decreasing'
        else:
            return 'stable'
    
    
    def _generate_insights(self, df: pd.DataFrame) -> List[str]:
        """Generate key insights from data"""
        insights = []
        
        # Check positive sentiment
        if 'positive' in df.columns:
            avg_positive = df['positive'].mean()
            if avg_positive > 70:
                insights.append(f"Strong positive sentiment at {avg_positive:.1f}%")
            elif avg_positive < 50:
                insights.append(f"Low positive sentiment at {avg_positive:.1f}% - action may be needed")
        
        # Check negative sentiment
        if 'negative' in df.columns:
            avg_negative = df['negative'].mean()
            if avg_negative > 30:
                insights.append(f"High negative sentiment at {avg_negative:.1f}% - immediate attention required")
        
        # Check volume trends
        if 'total' in df.columns and len(df) > 7:
            recent_avg = df['total'].tail(7).mean()
            overall_avg = df['total'].mean()
            
            if recent_avg > overall_avg * 1.2:
                insights.append("Mention volume increasing significantly")
            elif recent_avg < overall_avg * 0.8:
                insights.append("Mention volume decreasing")
        
        # Check volatility
        if 'positive' in df.columns:
            volatility = df['positive'].std()
            if volatility > 15:
                insights.append("High sentiment volatility detected")
        
        return insights
    
    
    def prepare_dashboard_data(self, historical_data: List[Dict], 
                               predictions: Dict) -> Dict:
        """
        Prepare data for dashboard visualization
        
        Args:
            historical_data: Historical sentiment data
            predictions: Prediction data
            
        Returns:
            Dashboard-ready data
        """
        return {
            'historical': self.aggregate_historical_data(historical_data),
            'predictions': predictions,
            'summary': self.generate_summary_report(historical_data),
            'spikes': self.detect_sentiment_spikes(historical_data),
            'generated_at': datetime.utcnow().isoformat()
        }


# Example usage
if __name__ == "__main__":
    processor = DataProcessor()
    
    # Generate sample data
    sample_data = []
    for i in range(30):
        sample_data.append({
            'date': datetime.now() - timedelta(days=29-i),
            'positive': 70 + np.random.randn() * 5,
            'negative': 20 + np.random.randn() * 3,
            'neutral': 10 + np.random.randn() * 2,
            'total': np.random.randint(800, 1500)
        })
    
    print("=== Aggregating Historical Data ===")
    aggregated = processor.aggregate_historical_data(sample_data)
    print(f"Average positive: {aggregated['summary']['avg_positive']:.2f}%")
    print(f"Trend: {aggregated['summary']['sentiment_trend']}")
    
    print("\n=== Detecting Spikes ===")
    spikes = processor.detect_sentiment_spikes(sample_data)
    print(f"Detected {len(spikes)} spikes")
    
    print("\n=== Summary Report ===")
    report = processor.generate_summary_report(sample_data)
    print(f"Period: {report['period']['start']} to {report['period']['end']}")
    print(f"Total mentions: {report['volume']['total_mentions']}")
    print(f"Key insights: {len(report['key_insights'])}")
    for insight in report['key_insights']:
        print(f"  - {insight}")