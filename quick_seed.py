"""
Quick Seed Script - Generate test data without ML models
"""
import sqlite3
from datetime import datetime, timedelta
import random
import hashlib

def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def seed_database():
    print("Starting quick database seed...")

    conn = sqlite3.connect('sentiment_analysis.db')
    cursor = conn.cursor()

    # Create tables first
    print("Creating database tables...")
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

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_created_at ON sentiment_records(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_source ON sentiment_records(source)")

    conn.commit()
    print("✓ Tables created")

    # Sample texts with their known sentiments
    samples = [
        ("I absolutely love this product! Best purchase ever!", "positive", 0.95, 95.0, 3.0, 2.0),
        ("Terrible customer service. Very disappointed.", "negative", 0.92, 5.0, 92.0, 3.0),
        ("The product is okay, works as expected.", "neutral", 0.88, 40.0, 20.0, 40.0),
        ("Amazing quality and fast delivery!", "positive", 0.94, 94.0, 4.0, 2.0),
        ("Not worth the price. Expected better.", "negative", 0.89, 8.0, 89.0, 3.0),
        ("Good product but shipping took long.", "neutral", 0.85, 60.0, 30.0, 10.0),
        ("Excellent! Exceeded expectations!", "positive", 0.96, 96.0, 2.0, 2.0),
        ("Average product, nothing special.", "neutral", 0.87, 45.0, 25.0, 30.0),
        ("Worst experience ever. Do not buy!", "negative", 0.93, 3.0, 93.0, 4.0),
        ("Pretty good overall. Would buy again.", "positive", 0.90, 88.0, 8.0, 4.0),
    ]

    sources = ['twitter', 'facebook', 'reviews', 'surveys']

    # Generate data for the past 45 days to ensure enough for predictions
    print("Creating sentiment records for 45 days...")
    records_created = 0

    for days_ago in range(45, 0, -1):
        record_date = datetime.now() - timedelta(days=days_ago)

        # Generate 10-20 records per day
        num_records = random.randint(10, 20)

        for _ in range(num_records):
            text, sentiment, confidence, pos, neg, neu = random.choice(samples)
            source = random.choice(sources)
            text_hash = hash_text(text + str(random.randint(1, 10000)))

            # Add some randomness to scores
            pos += random.uniform(-5, 5)
            neg += random.uniform(-3, 3)
            neu += random.uniform(-2, 2)

            # Normalize scores
            total = pos + neg + neu
            pos = max(0, min(100, (pos / total) * 100))
            neg = max(0, min(100, (neg / total) * 100))
            neu = max(0, min(100, (neu / total) * 100))

            cursor.execute("""
                INSERT INTO sentiment_records
                (text_hash, sentiment, confidence, positive_score, negative_score, neutral_score, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (text_hash, sentiment, confidence, pos, neg, neu, source, record_date))

            records_created += 1

    conn.commit()
    print(f"✓ Created {records_created} sentiment records")

    # Create test users
    print("Creating test users...")
    users = [
        ('admin@sentimentdashboard.com', 'Admin@123', 'Admin User', 'admin'),
        ('analyst@test.com', 'Test@123', 'John Analyst', 'analyst'),
        ('manager@test.com', 'Test@123', 'Jane Manager', 'manager'),
        ('viewer@test.com', 'Test@123', 'Bob Viewer', 'viewer'),
    ]

    for email, password, name, role in users:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            cursor.execute("""
                INSERT INTO users (email, password_hash, name, role, gdpr_consent)
                VALUES (?, ?, ?, ?, ?)
            """, (email, password_hash, name, role, True))
            print(f"  ✓ Created user: {email}")
        except sqlite3.IntegrityError:
            print(f"  User {email} already exists")

    conn.commit()

    # Create predictions for next 7 days
    print("Creating predictions...")
    for days_ahead in range(1, 8):
        prediction_date = (datetime.now() + timedelta(days=days_ahead)).date()

        # Create realistic predictions with trend
        base_positive = 70 + (days_ahead * 0.5)  # Slight improving trend
        base_negative = 20 - (days_ahead * 0.2)
        base_neutral = 10 - (days_ahead * 0.3)

        cursor.execute("""
            INSERT INTO predictions
            (prediction_date, positive_score, negative_score, neutral_score, confidence, model_version)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            prediction_date,
            base_positive,
            base_negative,
            base_neutral,
            0.85 - (days_ahead * 0.02),
            'v1.0'
        ))

    conn.commit()
    print("✓ Created 7 days of predictions")

    conn.close()

    print("\n" + "="*50)
    print("✓ Database seeded successfully!")
    print("="*50)
    print("\nTest Users:")
    print("  admin@sentimentdashboard.com / Admin@123 (Admin)")
    print("  analyst@test.com / Test@123 (Analyst)")
    print("  manager@test.com / Test@123 (Manager)")
    print("  viewer@test.com / Test@123 (Viewer)")
    print("\nYou can now access the dashboard!")

if __name__ == "__main__":
    seed_database()
