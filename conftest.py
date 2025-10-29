"""
Pytest Configuration and Fixtures
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from core.database import Database
from core.sentiment_analyzer import SentimentAnalyzer
from core.cache_manager import CacheManager


@pytest.fixture
def app():
    """Create Flask app for testing"""
    flask_app.config['TESTING'] = True
    flask_app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    yield flask_app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def database():
    """Create database instance for testing"""
    db = Database()
    yield db


@pytest.fixture
def sentiment_analyzer():
    """Create sentiment analyzer instance"""
    analyzer = SentimentAnalyzer()
    yield analyzer


@pytest.fixture
def cache_manager():
    """Create cache manager instance"""
    cache = CacheManager()
    yield cache


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for testing"""
    # Create test user and login
    response = client.post('/api/auth/login', json={
        'email': 'admin@sentimentdashboard.com',
        'password': 'Admin@123'
    })
    
    if response.status_code == 200:
        data = response.get_json()
        token = data.get('token')
        return {'Authorization': f'Bearer {token}'}
    
    return {}


@pytest.fixture
def sample_texts():
    """Sample texts for testing"""
    return [
        "I love this product! It's amazing!",
        "Terrible experience, very disappointed.",
        "It's okay, nothing special.",
        "Best purchase I've ever made!",
        "Would not recommend to anyone."
    ]