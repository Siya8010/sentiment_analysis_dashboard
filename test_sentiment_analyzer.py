"""
Tests for Sentiment Analyzer
"""

import pytest


def test_sentiment_analyzer_initialization(sentiment_analyzer):
    """Test sentiment analyzer initializes correctly"""
    assert sentiment_analyzer is not None
    assert sentiment_analyzer.model is not None
    assert sentiment_analyzer.tokenizer is not None


def test_analyze_positive_sentiment(sentiment_analyzer):
    """Test analyzing positive sentiment"""
    text = "I absolutely love this product! It's amazing and works perfectly!"
    result = sentiment_analyzer.analyze(text)
    
    assert result is not None
    assert 'sentiment' in result
    assert 'confidence' in result
    assert 'scores' in result
    assert result['sentiment'] == 'positive'
    assert result['confidence'] > 0.5


def test_analyze_negative_sentiment(sentiment_analyzer):
    """Test analyzing negative sentiment"""
    text = "This is terrible! Worst experience ever. Do not recommend."
    result = sentiment_analyzer.analyze(text)
    
    assert result is not None
    assert result['sentiment'] == 'negative'
    assert result['scores']['negative'] > result['scores']['positive']


def test_analyze_neutral_sentiment(sentiment_analyzer):
    """Test analyzing neutral sentiment"""
    text = "The product is okay. It works as expected, nothing more."
    result = sentiment_analyzer.analyze(text)
    
    assert result is not None
    assert 'sentiment' in result


def test_analyze_empty_text(sentiment_analyzer):
    """Test analyzing empty text"""
    result = sentiment_analyzer.analyze("")
    
    assert result is not None
    assert 'error' in result


def test_analyze_batch(sentiment_analyzer, sample_texts):
    """Test batch sentiment analysis"""
    results = sentiment_analyzer.analyze_batch(sample_texts)
    
    assert len(results) == len(sample_texts)
    assert all('sentiment' in r for r in results)
    assert all('confidence' in r for r in results)


def test_preprocess_text(sentiment_analyzer):
    """Test text preprocessing"""
    text = "Check out http://example.com @user #hashtag !!! "
    processed = sentiment_analyzer.preprocess_text(text)
    
    assert 'http://' not in processed
    assert '@user' not in processed


def test_get_stats(sentiment_analyzer):
    """Test getting analyzer statistics"""
    stats = sentiment_analyzer.get_stats()
    
    assert 'model_name' in stats
    assert 'device' in stats
    assert 'current_accuracy' in stats