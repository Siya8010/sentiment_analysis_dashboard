"""
Database Module
Handles all database operations with PostgreSQL
Includes GDPR compliance features
"""

import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
from psycopg2.pool import SimpleConnectionPool
import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        """Initialize database connection pool"""
        self.pool = SimpleConnectionPool(
            minconn=1,
            maxconn=20,
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', 5432),
            database=os.getenv('DB_NAME', 'sentiment_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'password')
        )
        
        logger.info("Database connection pool initialized")
        self._create_tables()
    
    
    def _get_connection(self):
        """Get connection from pool"""
        return self.pool.getconn()
    
    
    def _return_connection(self, conn):
        """Return connection to pool"""
        self.pool.putconn(conn)
    
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
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
            
            # Historical aggregated data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentiment_daily_aggregates (
                    id SERIAL PRIMARY KEY,
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
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    action VARCHAR(100) NOT NULL,
                    details TEXT,
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model training records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_training_history (
                    id SERIAL PRIMARY KEY,
                    model_type VARCHAR(50) NOT NULL,
                    accuracy FLOAT NOT NULL,
                    training_samples INTEGER NOT NULL,
                    trained_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Predictions cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    prediction_date DATE NOT NULL,
                    positive_score FLOAT NOT NULL,
                    negative_score FLOAT NOT NULL,
                    neutral_score FLOAT NOT NULL,
                    confidence FLOAT NOT NULL,
                    model_version VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Social media integrations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS social_media_data (
                    id SERIAL PRIMARY KEY,
                    source VARCHAR(50) NOT NULL,
                    external_id VARCHAR(255),
                    text TEXT NOT NULL,
                    author VARCHAR(255),
                    sentiment VARCHAR(20),
                    engagement_score INTEGER,
                    posted_at TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes (PostgreSQL)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_created_at ON sentiment_records (created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_source ON sentiment_records (source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_type ON sentiment_records (sentiment)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_agg_date ON sentiment_daily_aggregates (date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_agg_source ON sentiment_daily_aggregates (source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions (prediction_date)")
            
            conn.commit()
            logger.info("Database tables created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating tables: {str(e)}")
            raise
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            password_hash = self._hash_password(password)
            
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, role, gdpr_consent)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (email, password_hash, name, role, gdpr_consent))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"User created: {email}")
            
            return {'success': True, 'user_id': user_id}
            
        except psycopg2.IntegrityError:
            conn.rollback()
            return {'success': False, 'error': 'Email already exists'}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            password_hash = self._hash_password(password)
            
            cursor.execute("""
                SELECT id, email, name, role, created_at
                FROM users
                WHERE email = %s AND password_hash = %s
            """, (email, password_hash))
            
            user = cursor.fetchone()
            
            return dict(user) if user else None
            
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return None
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT id, email, name, role, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            return dict(user) if user else None
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (admin only)"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT id, email, name, role, created_at
                FROM users
                ORDER BY created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    # ============= SENTIMENT RECORDS =============
    
    def log_analysis(self, user_id: int, text: str, result: Dict):
        """Log a sentiment analysis"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            text_hash = self._hash_text(text)
            
            cursor.execute("""
                INSERT INTO sentiment_records 
                (user_id, text_hash, sentiment, confidence, positive_score, 
                 negative_score, neutral_score, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error logging analysis: {str(e)}")
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def bulk_insert_sentiment_data(self, data: List[Dict], source: str = 'api'):
        """Bulk insert sentiment data"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            values = [
                (
                    self._hash_text(item.get('text', '')),
                    item.get('sentiment', {}).get('sentiment', 'neutral'),
                    item.get('sentiment', {}).get('confidence', 0.0),
                    item.get('sentiment', {}).get('scores', {}).get('positive', 0.0),
                    item.get('sentiment', {}).get('scores', {}).get('negative', 0.0),
                    item.get('sentiment', {}).get('scores', {}).get('neutral', 0.0),
                    source
                )
                for item in data
            ]
            
            execute_batch(cursor, """
                INSERT INTO sentiment_records 
                (text_hash, sentiment, confidence, positive_score, 
                 negative_score, neutral_score, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, values)
            
            conn.commit()
            logger.info(f"Bulk inserted {len(values)} sentiment records")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error bulk inserting: {str(e)}")
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def get_historical_sentiment(self, days: int = 7, source: str = 'all') -> List[Dict]:
        """Get historical sentiment data"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            if source == 'all':
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        AVG(positive_score) as positive,
                        AVG(negative_score) as negative,
                        AVG(neutral_score) as neutral,
                        COUNT(*) as total
                    FROM sentiment_records
                    WHERE created_at >= %s
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
                    WHERE created_at >= %s AND source = %s
                    GROUP BY DATE(created_at)
                    ORDER BY date ASC
                """, (start_date, source))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def get_sentiment_trends(self, period: str = 'week') -> List[Dict]:
        """Get sentiment trends"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        days_map = {'day': 1, 'week': 7, 'month': 30}
        days = days_map.get(period, 7)
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    source,
                    sentiment,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM sentiment_records
                WHERE created_at >= %s
                GROUP BY DATE(created_at), source, sentiment
                ORDER BY date ASC
            """, (start_date,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    # ============= AUDIT LOGS =============
    
    def log_audit_event(self, user_id: int, action: str, ip_address: str, details: str = None):
        """Log audit event for GDPR compliance"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, details, ip_address)
                VALUES (%s, %s, %s, %s)
            """, (user_id, action, details, ip_address))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error logging audit event: {str(e)}")
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    # ============= MODEL MANAGEMENT =============
    
    def log_model_retrain(self, user_id: int, result: Dict):
        """Log model retraining event"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO model_training_history 
                (model_type, accuracy, training_samples, trained_by)
                VALUES (%s, %s, %s, %s)
            """, (
                'sentiment_classifier',
                result.get('accuracy', 0.0),
                result.get('training_samples', 0),
                user_id
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error logging model retrain: {str(e)}")
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def get_training_data(self, days: int = 30) -> List[Dict]:
        """Get training data for model retraining"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT 
                    sentiment as label,
                    positive_score,
                    negative_score,
                    neutral_score,
                    confidence
                FROM sentiment_records
                WHERE created_at >= %s AND confidence > 0.8
                LIMIT 10000
            """, (start_date,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    # ============= STATISTICS =============
    
    def get_total_analyses(self) -> int:
        """Get total number of analyses"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM sentiment_records")
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def get_api_calls_count(self, days: int = 1) -> int:
        """Get API call count"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT COUNT(*) FROM audit_logs
                WHERE created_at >= %s
            """, (start_date,))
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def get_active_users_count(self, days: int = 7) -> int:
        """Get active users count"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            start_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM audit_logs
                WHERE created_at >= %s
            """, (start_date,))
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            self._return_connection(conn)
    
    
    def get_avg_response_time(self) -> float:
        """Get average API response time (mock)"""
        return 245.6  # milliseconds
    
    
    def get_crm_export_data(self, days: int = 7) -> List[Dict]:
        """Get data formatted for CRM export"""
        return self.get_historical_sentiment(days=days)
    
    
    def check_connection(self) -> bool:
        """Check database connection health"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            self._return_connection(conn)
            return True
        except:
            return False