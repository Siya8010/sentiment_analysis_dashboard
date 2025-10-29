"""
Seed Data Script
Populates database with sample data for testing
"""

import sys
import os

try:
    from database_sqlite import Database
except ImportError:
    from database import Database

from sentiment_analyzer import SentimentAnalyzer
from datetime import datetime, timedelta
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_data():
    """Seed database with sample data"""
    try:
        logger.info("Starting data seeding...")
        
        db = Database()
        analyzer = SentimentAnalyzer()
        
        # Sample tweets/comments
        sample_texts = [
            "I absolutely love this product! Best purchase ever!",
            "Terrible customer service. Very disappointed.",
            "The product is okay, works as expected.",
            "Amazing quality and fast delivery! Highly recommend!",
            "Not worth the price. Expected better quality.",
            "Good product but shipping took too long.",
            "Excellent! Exceeded all my expectations!",
            "Average product, nothing special.",
            "Worst experience ever. Do not buy!",
            "Pretty good overall. Would buy again.",
            "Customer support was very helpful and friendly.",
            "Product broke after one week. Poor quality.",
            "Great value for money! Very satisfied.",
            "Mediocre. There are better alternatives.",
            "Outstanding service and product quality!",
            "Disappointed with the performance.",
            "Works perfectly! No complaints.",
            "Not as advertised. Misleading description.",
            "Fantastic! Will recommend to friends.",
            "It's fine. Does the job.",
        ]
        
        sources = ['twitter', 'facebook', 'reviews', 'surveys']
        
        # Create sample sentiment data for past 30 days
        logger.info("Creating sentiment records...")
        
        records_created = 0
        
        for days_ago in range(30, 0, -1):
            date = datetime.now() - timedelta(days=days_ago)
            
            # Generate 5-15 records per day (reduced for speed)
            num_records = random.randint(5, 15)
            
            for _ in range(num_records):
                text = random.choice(sample_texts)
                source = random.choice(sources)
                
                # Analyze sentiment
                result = analyzer.analyze(text)
                
                # Insert into database using SQLite-compatible method
                sentiment_data = [{
                    'text': text,
                    'sentiment': {
                        'sentiment': result['sentiment'],
                        'confidence': result['confidence'],
                        'scores': result['scores']
                    }
                }]
                
                db.bulk_insert_sentiment_data(sentiment_data, source)
                records_created += 1
        
        logger.info(f"✓ Created {records_created} sample sentiment records for 30 days")
        
        # Create sample users
        logger.info("Creating sample users...")
        
        test_users = [
            {'email': 'analyst@test.com', 'password': 'Test@123', 'name': 'John Analyst', 'role': 'analyst'},
            {'email': 'manager@test.com', 'password': 'Test@123', 'name': 'Jane Manager', 'role': 'manager'},
            {'email': 'viewer@test.com', 'password': 'Test@123', 'name': 'Bob Viewer', 'role': 'viewer'},
        ]
        
        for user in test_users:
            result = db.create_user(
                email=user['email'],
                password=user['password'],
                name=user['name'],
                role=user['role'],
                gdpr_consent=True
            )
            
            if result['success']:
                logger.info(f"  ✓ Created user: {user['email']}")
            else:
                logger.info(f"  User {user['email']} already exists")
        
        # Add some predictions data
        logger.info("Creating sample predictions...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            for days_ahead in range(1, 8):
                prediction_date = datetime.now() + timedelta(days=days_ahead)
                
                cursor.execute("""
                    INSERT INTO predictions 
                    (prediction_date, positive_score, negative_score, neutral_score, confidence, model_version)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    prediction_date.date(),
                    random.uniform(0.6, 0.9),  # positive
                    random.uniform(0.1, 0.3),  # negative
                    random.uniform(0.1, 0.3),  # neutral
                    random.uniform(0.7, 0.95), # confidence
                    'v1.0'
                ))
        
        logger.info("✓ Data seeding completed successfully!")
        logger.info("\nTest Users Created:")
        logger.info("  admin@sentimentdashboard.com / Admin@123 (Admin)")
        logger.info("  analyst@test.com / Test@123 (Analyst)")
        logger.info("  manager@test.com / Test@123 (Manager)")
        logger.info("  viewer@test.com / Test@123 (Viewer)")
        logger.info("\nAccess the dashboard with any of these accounts!")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Error seeding data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = seed_data()
    sys.exit(0 if success else 1)