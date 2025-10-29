"""
SQLite Database Module
Handles all database operations with SQLite for easy setup
Includes GDPR compliance features
"""

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import json
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        """Initialize SQLite database"""
        self.db_path = "sentiment_analysis.db"
        # Create data directory if using data/ path in the future
        # os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        logger.info("SQLite database initialized")
        self._create_tables()
    
    @contextmanager
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    gdpr_consent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Sentiment analysis records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    text_hash VARCHAR(64),
                    sentiment VARCHAR(20) NOT NULL,
                    confidence FLOAT NOT NULL,
                    positive_score FLOAT NOT NULL,
                    negative_score FLOAT NOT NULL,
                    neutral_score FLOAT NOT NULL,
                    source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_created_at ON sentiment_records(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_source ON sentiment_records(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_type ON sentiment_records(sentiment)")
            
            # Historical aggregated data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_daily_aggregates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE NOT NULL,
                    source VARCHAR(50),
                    positive_avg FLOAT NOT NULL,
                    negative_avg FLOAT NOT NULL,
                    neutral_avg FLOAT NOT NULL,
                    total_mentions INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Audit logs for GDPR compliance
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action VARCHAR(100) NOT NULL,
                    details TEXT,
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model training records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_training_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_type VARCHAR(50) NOT NULL,
                    accuracy FLOAT NOT NULL,
                    training_samples INTEGER NOT NULL,
                    trained_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Predictions cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_date DATE NOT NULL,
                    positive_score FLOAT NOT NULL,
                    negative_score FLOAT NOT NULL,
                    neutral_score FLOAT NOT NULL,
                    confidence FLOAT NOT NULL,
                    model_version VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logger.info("SQLite database tables created successfully")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _hash_text(self, text: str) -> str:
        """Hash text for deduplication"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    # ============= USER MANAGEMENT =============
    
    def create_user(self, email: str, password: str, name: str, role: str = 'viewer', 
                    gdpr_consent: bool = False) -> Dict:
        """Create a new user"""
        try:
            password_hash = self._hash_password(password)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (email, password_hash, name, role, gdpr_consent)
                    VALUES (?, ?, ?, ?, ?)
                """, (email, password_hash, name, role, gdpr_consent))
                
                user_id = cursor.lastrowid
                
            logger.info(f"User created: {email}")
            return {'success': True, 'user_id': user_id}
            
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Email already exists'}
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        try:
            password_hash = self._hash_password(password)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, email, name, role, created_at
                    FROM users
                    WHERE email = ? AND password_hash = ?
                """, (email, password_hash))
                
                user = cursor.fetchone()
                return dict(user) if user else None
                
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, role, created_at
                FROM users
                WHERE id = ?
            """, (user_id,))
            
            user = cursor.fetchone()
            return dict(user) if user else None
    
    # ============= SENTIMENT RECORDS =============
    
    def log_analysis(self, user_id: int, text: str, result: Dict):
        """Log a sentiment analysis"""
        try:
            text_hash = self._hash_text(text)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sentiment_records 
                    (user_id, text_hash, sentiment, confidence, positive_score, 
                     negative_score, neutral_score, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    text_hash,
                    result.get('sentiment', 'neutral'),
                    result.get('confidence', 0.0),
                    result.get('scores', {}).get('positive', 0.0),
                    result.get('scores', {}).get('negative', 0.0),
                    result.get('scores', {}).get('neutral', 0.0),
                    'api'
                ))
                
        except Exception as e:
            logger.error(f"Error logging analysis: {str(e)}")
    
    def bulk_insert_sentiment_data(self, data: List[Dict], source: str = 'api'):
        """Bulk insert sentiment data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for item in data:
                    cursor.execute("""
                        INSERT INTO sentiment_records 
                        (text_hash, sentiment, confidence, positive_score, 
                         negative_score, neutral_score, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self._hash_text(item.get('text', '')),
                        item.get('sentiment', {}).get('sentiment', 'neutral'),
                        item.get('sentiment', {}).get('confidence', 0.0),
                        item.get('sentiment', {}).get('scores', {}).get('positive', 0.0),
                        item.get('sentiment', {}).get('scores', {}).get('negative', 0.0),
                        item.get('sentiment', {}).get('scores', {}).get('neutral', 0.0),
                        source
                    ))
                
            logger.info(f"Bulk inserted {len(data)} sentiment records")
            
        except Exception as e:
            logger.error(f"Error bulk inserting: {str(e)}")
    
    def get_historical_sentiment(self, days: int = 7, source: str = 'all') -> List[Dict]:
        """Get historical sentiment data"""
        start_date = datetime.now() - timedelta(days=days)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if source == 'all':
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        AVG(positive_score) as positive,
                        AVG(negative_score) as negative,
                        AVG(neutral_score) as neutral,
                        COUNT(*) as total
                    FROM sentiment_records
                    WHERE created_at >= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                """, (start_date,))
            else:
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        AVG(positive_score) as positive,
                        AVG(negative_score) as negative,
                        AVG(neutral_score) as neutral,
                        COUNT(*) as total
                    FROM sentiment_records
                    WHERE created_at >= ? AND source = ?
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                """, (start_date, source))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ============= AUDIT LOGS =============
    
    def log_audit_event(self, user_id: int, action: str, ip_address: str, details: str = None):
        """Log audit event for GDPR compliance"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, action, details, ip_address)
                    VALUES (?, ?, ?, ?)
                """, (user_id, action, details, ip_address))
                
        except Exception as e:
            logger.error(f"Error logging audit event: {str(e)}")
    
    # ============= STATISTICS =============
    
    def get_total_analyses(self) -> int:
        """Get total number of analyses"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sentiment_records")
            return cursor.fetchone()[0]
    
    def check_connection(self) -> bool:
        """Check database connection health"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except:
            return False

    def get_sentiment_trends(self, period: str = 'week') -> List[Dict]:
        """Get sentiment trends for a period"""
        days_map = {'day': 1, 'week': 7, 'month': 30}
        days = days_map.get(period, 7)
        start_date = datetime.now() - timedelta(days=days)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    DATE(created_at) as date,
                    sentiment,
                    source,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM sentiment_records
                WHERE created_at >= ?
                GROUP BY DATE(created_at), sentiment, source
                ORDER BY date ASC
            """, (start_date,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_crm_export_data(self, days: int = 7) -> List[Dict]:
        """Get data formatted for CRM export"""
        return self.get_historical_sentiment(days=days)

    def get_training_data(self, days: int = 30) -> List[Dict]:
        """Get training data for model retraining"""
        start_date = datetime.now() - timedelta(days=days)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT text_hash, sentiment, confidence
                FROM sentiment_records
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """, (start_date,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_api_calls_count(self, days: int = 1) -> int:
        """Get API calls count"""
        start_date = datetime.now() - timedelta(days=days)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM sentiment_records
                WHERE created_at >= ?
            """, (start_date,))
            return cursor.fetchone()[0]

    def get_active_users_count(self, days: int = 7) -> int:
        """Get active users count"""
        start_date = datetime.now() - timedelta(days=days)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM audit_logs
                WHERE created_at >= ? AND user_id IS NOT NULL
            """, (start_date,))
            return cursor.fetchone()[0]

    def get_avg_response_time(self) -> float:
        """Get average response time (mock implementation)"""
        return 245.0

    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, role, created_at
                FROM users
                ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def log_model_retrain(self, user_id: int, result: Dict):
        """Log model retraining event"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO model_training_history
                    (model_type, accuracy, training_samples, trained_by)
                    VALUES (?, ?, ?, ?)
                """, (
                    'sentiment_classifier',
                    result.get('accuracy', 0.0),
                    result.get('training_samples', 0),
                    user_id
                ))

        except Exception as e:
            logger.error(f"Error logging model retrain: {str(e)}")