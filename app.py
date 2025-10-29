"""
AI-Powered Sentiment Analysis Dashboard - Backend API
Main Flask Application with all endpoints
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import tweepy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import os
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import custom modules
from sentiment_analyzer import SentimentAnalyzer
from predictive_model import PredictiveModel
from data_processor import DataProcessor
from twitter_integration import TwitterAPI
# Select database backend
DB_DRIVER = os.getenv('DB_DRIVER', 'sqlite').lower()
if DB_DRIVER == 'sqlite':
    from database_sqlite import Database
else:
    from database import Database

from gdpr_compliance import GDPRHandler
from cache_manager import CacheManager

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Robust CORS config for development: allow frontend and handle preflight
CORS(app, resources={r"/*": {"origins": ["http://localhost:3002"]}}, supports_credentials=True, allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
jwt = JWTManager(app)

# Initialize components
sentiment_analyzer = SentimentAnalyzer()
predictive_model = PredictiveModel()
data_processor = DataProcessor()
twitter_api = TwitterAPI()
db = Database()
gdpr_handler = GDPRHandler()
cache = CacheManager()

# Role-based access control decorator
def role_required(allowed_roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = db.get_user(user_id)
            
            if user['role'] not in allowed_roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ============= AUTHENTICATION ENDPOINTS =============

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = db.authenticate_user(email, password)
    
    if user:
        access_token = create_access_token(identity=user['id'])
        
        # Log login event
        db.log_audit_event(user['id'], 'login', request.remote_addr)
        
        return jsonify({
            'token': access_token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role']
            }
        }), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/auth/register', methods=['POST'])
def register():
    """User registration endpoint"""
    data = request.get_json()
    
    # GDPR: Validate consent
    if not data.get('gdpr_consent'):
        return jsonify({'error': 'GDPR consent required'}), 400
    
    result = db.create_user(
        email=data['email'],
        password=data['password'],
        name=data['name'],
        role=data.get('role', 'viewer'),
        gdpr_consent=True
    )
    
    if result['success']:
        return jsonify({'message': 'User created successfully'}), 201
    
    return jsonify({'error': result['error']}), 400


# ============= SENTIMENT ANALYSIS ENDPOINTS =============

@app.route('/api/sentiment/analyze', methods=['POST'])
@jwt_required()
def analyze_sentiment():
    """Analyze sentiment of provided text"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    # Check cache first
    cache_key = f"sentiment:{hash(text)}"
    cached_result = cache.get(cache_key)
    
    if cached_result:
        return jsonify(cached_result), 200
    
    # Analyze sentiment
    result = sentiment_analyzer.analyze(text)
    
    # Cache result for 1 hour
    cache.set(cache_key, result, ttl=3600)
    
    # Log analysis
    user_id = get_jwt_identity()
    db.log_analysis(user_id, text[:100], result)
    
    return jsonify(result), 200


@app.route('/api/sentiment/batch', methods=['POST'])
@jwt_required()
@role_required(['admin', 'analyst'])
def batch_sentiment_analysis():
    """Batch sentiment analysis for multiple texts"""
    data = request.get_json()
    texts = data.get('texts', [])
    
    if not texts or len(texts) > 1000:
        return jsonify({'error': 'Provide 1-1000 texts'}), 400
    
    results = sentiment_analyzer.analyze_batch(texts)
    
    return jsonify({
        'total': len(texts),
        'results': results,
        'summary': {
            'positive': sum(1 for r in results if r['sentiment'] == 'positive'),
            'negative': sum(1 for r in results if r['sentiment'] == 'negative'),
            'neutral': sum(1 for r in results if r['sentiment'] == 'neutral')
        }
    }), 200


@app.route('/api/sentiment/realtime', methods=['GET'])
def get_realtime_sentiment():
    """Get real-time sentiment data from various sources"""
    source = request.args.get('source', 'all')
    limit = int(request.args.get('limit', 100))
    product = request.args.get('product') or request.args.get('keywords')

    # Create cache key
    cache_key = f"realtime:{source}:{product}:{limit}"
    cached_result = cache.get(cache_key)

    if cached_result:
        return jsonify(cached_result), 200

    data = []
    try:
        if source in ['all', 'twitter']:
            if product:
                keywords = [k.strip() for k in product.split(',') if k.strip()]
                if keywords:
                    twitter_data = twitter_api.fetch_tweets(keywords=keywords, count=limit)
                else:
                    twitter_data = twitter_api.get_recent_mentions(limit=limit)
            else:
                twitter_data = twitter_api.get_recent_mentions(limit=limit)
            data.extend(twitter_data)
    except tweepy.TooManyRequests:
        return jsonify({'error': 'Twitter rate limit exceeded. Please try again in 15 minutes.'}), 429
    except Exception as e:
        logger.error(f"Error fetching realtime data: {str(e)}")
        return jsonify({'error': 'Failed to fetch live data. Using cached data if available.'}), 500

    processed_data = data_processor.process_realtime_data(data)

    result = {
        'timestamp': datetime.utcnow().isoformat(),
        'source': source,
        'count': len(processed_data),
        'data': processed_data
    }

    # Cache for 2 minutes to reduce API calls
    cache.set(cache_key, result, ttl=120)

    return jsonify(result), 200


# ============= HISTORICAL DATA ENDPOINTS =============

@app.route('/api/analytics/historical', methods=['GET'])
def get_historical_data():
    """Get historical sentiment trends"""
    days = int(request.args.get('days', 7))
    source = request.args.get('source', 'all')
    if days > 90:
        return jsonify({'error': 'Maximum 90 days allowed'}), 400
    cache_key = f"historical:{days}:{source}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return jsonify(cached_data), 200
    historical_data = db.get_historical_sentiment(days=days, source=source)
    processed = data_processor.aggregate_historical_data(historical_data)
    cache.set(cache_key, processed, ttl=1800)
    return jsonify(processed), 200


@app.route('/api/analytics/trends', methods=['GET'])
@jwt_required()
def get_sentiment_trends():
    """Get sentiment trend analysis"""
    period = request.args.get('period', 'week')  # day, week, month
    
    trends = db.get_sentiment_trends(period)
    
    # Calculate insights
    insights = data_processor.calculate_trend_insights(trends)
    
    return jsonify({
        'period': period,
        'trends': trends,
        'insights': insights
    }), 200


# ============= PREDICTIVE ANALYTICS ENDPOINTS =============

@app.route('/api/predictions/sentiment', methods=['GET'])
def predict_sentiment():
    """Get sentiment predictions for next N days"""
    days = int(request.args.get('days', 7))
    if days > 30:
        return jsonify({'error': 'Maximum 30 days prediction allowed'}), 400
    cache_key = f"prediction:{days}"
    cached_prediction = cache.get(cache_key)
    if cached_prediction:
        return jsonify(cached_prediction), 200
    historical_data = db.get_historical_sentiment(days=30)
    predictions = predictive_model.predict(historical_data, forecast_days=days)
    cache.set(cache_key, predictions, ttl=3600)
    return jsonify(predictions), 200


@app.route('/api/predictions/alerts', methods=['GET'])
@jwt_required()
def get_predictive_alerts():
    """Get predictive alerts for potential PR crises"""
    predictions = predictive_model.get_latest_predictions()
    
    alerts = []
    
    # Check for negative sentiment spikes
    for pred in predictions:
        if pred['negative_score'] > 40 and pred['confidence'] > 0.7:
            alerts.append({
                'severity': 'high',
                'type': 'negative_spike',
                'date': pred['date'],
                'confidence': pred['confidence'],
                'message': f"High negative sentiment predicted ({pred['negative_score']:.1f}%)"
            })
    
    return jsonify({
        'alerts': alerts,
        'count': len(alerts)
    }), 200


# ============= INTEGRATION ENDPOINTS =============

@app.route('/api/integrations/twitter/sync', methods=['POST'])
def sync_twitter():
    """Sync Twitter data for given keywords"""
    data = request.get_json()
    keywords = data.get('keywords', [])
    if not keywords:
        return jsonify({'error': 'No keywords provided'}), 400
    try:
        synced, timestamp = twitter_api.sync(keywords)
    except tweepy.TooManyRequests:
        return jsonify({'error': 'Twitter rate limit exceeded. Please try again later.'}), 429
    return jsonify({'synced': synced, 'timestamp': timestamp}), 200


@app.route('/api/integrations/crm/export', methods=['GET'])
@jwt_required()
@role_required(['admin', 'manager'])
def export_to_crm():
    """Export sentiment data to CRM system"""
    days = int(request.args.get('days', 7))
    
    # Get aggregated sentiment data
    data = db.get_crm_export_data(days=days)
    
    # Format for CRM (Salesforce format example)
    crm_data = data_processor.format_for_crm(data)
    
    return jsonify(crm_data), 200


# ============= GDPR COMPLIANCE ENDPOINTS =============

@app.route('/api/gdpr/user-data', methods=['GET'])
@jwt_required()
def get_user_data():
    """GDPR: Get all user data"""
    user_id = get_jwt_identity()
    
    # Collect all user data
    user_data = gdpr_handler.collect_user_data(user_id)
    
    return jsonify(user_data), 200


@app.route('/api/gdpr/delete-account', methods=['DELETE'])
@jwt_required()
def delete_account():
    """GDPR: Delete user account and all associated data"""
    user_id = get_jwt_identity()
    
    # Anonymize or delete user data
    result = gdpr_handler.delete_user_data(user_id)
    
    if result['success']:
        return jsonify({'message': 'Account deleted successfully'}), 200
    
    return jsonify({'error': 'Failed to delete account'}), 500


@app.route('/api/gdpr/consent', methods=['PUT'])
@jwt_required()
def update_consent():
    """GDPR: Update user consent preferences"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    result = gdpr_handler.update_consent(user_id, data)
    
    return jsonify(result), 200


# ============= ADMIN ENDPOINTS =============

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
@role_required(['admin'])
def get_all_users():
    """Get all users (admin only)"""
    users = db.get_all_users()
    
    # Remove sensitive data
    safe_users = [{
        'id': u['id'],
        'email': u['email'],
        'name': u['name'],
        'role': u['role'],
        'created_at': u['created_at']
    } for u in users]
    
    return jsonify(safe_users), 200


@app.route('/api/admin/model/retrain', methods=['POST'])
@jwt_required()
@role_required(['admin'])
def retrain_model():
    """Trigger model retraining"""
    # Get recent data for retraining
    training_data = db.get_training_data(days=30)
    
    # Retrain model
    result = sentiment_analyzer.retrain(training_data)
    
    # Log retraining event
    user_id = get_jwt_identity()
    db.log_model_retrain(user_id, result)
    
    return jsonify({
        'status': 'success',
        'accuracy': result['accuracy'],
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/admin/metrics', methods=['GET'])
@jwt_required()
@role_required(['admin'])
def get_system_metrics():
    """Get system performance metrics"""
    metrics = {
        'model_accuracy': sentiment_analyzer.get_current_accuracy(),
        'total_analyses': db.get_total_analyses(),
        'api_calls_today': db.get_api_calls_count(days=1),
        'active_users': db.get_active_users_count(days=7),
        'cache_hit_rate': cache.get_hit_rate(),
        'avg_response_time_ms': db.get_avg_response_time()
    }
    
    return jsonify(metrics), 200


# ============= HEALTH CHECK =============

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': db.check_connection(),
            'cache': cache.check_connection(),
            'twitter_api': twitter_api.check_connection()
        }
    }), 200


# ============= ERROR HANDLERS =============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.getenv('PORT', 5000)))