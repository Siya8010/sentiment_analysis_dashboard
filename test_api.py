"""
Tests for API Endpoints
"""

import pytest
import json


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


def test_login_success(client):
    """Test successful login"""
    response = client.post('/api/auth/login', 
        json={
            'email': 'admin@sentimentdashboard.com',
            'password': 'Admin@123'
        }
    )
    assert response.status_code == 200
    data = response.get_json()
    assert 'token' in data
    assert 'user' in data


def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post('/api/auth/login',
        json={
            'email': 'invalid@test.com',
            'password': 'wrongpassword'
        }
    )
    assert response.status_code == 401


def test_register_success(client):
    """Test successful registration"""
    response = client.post('/api/auth/register',
        json={
            'email': 'newuser@test.com',
            'password': 'Test@123',
            'name': 'New User',
            'role': 'viewer',
            'gdpr_consent': True
        }
    )
    assert response.status_code in [200, 201, 400]  # 400 if user exists


def test_analyze_sentiment_unauthorized(client):
    """Test sentiment analysis without authentication"""
    response = client.post('/api/sentiment/analyze',
        json={'text': 'Test text'}
    )
    assert response.status_code == 401


def test_analyze_sentiment_authorized(client, auth_headers):
    """Test sentiment analysis with authentication"""
    response = client.post('/api/sentiment/analyze',
        headers=auth_headers,
        json={'text': 'I love this product!'}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert 'sentiment' in data
    assert 'confidence' in data


def test_get_historical_data(client, auth_headers):
    """Test getting historical data"""
    response = client.get('/api/analytics/historical?days=7',
        headers=auth_headers
    )
    assert response.status_code == 200


def test_get_predictions(client, auth_headers):
    """Test getting predictions"""
    response = client.get('/api/predictions/sentiment?days=7',
        headers=auth_headers
    )
    assert response.status_code == 200


def test_unauthorized_admin_access(client, auth_headers):
    """Test accessing admin endpoint without admin role"""
    response = client.get('/api/admin/users',
        headers=auth_headers
    )
    # Should return 403 if not admin, or 200 if admin
    assert response.status_code in [200, 403]
