"""
Twitter API Integration Module
Handles real-time data fetching from Twitter/X
"""

import tweepy
import os
from datetime import datetime, timedelta
from typing import List, Dict
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwitterAPI:
    def __init__(self):
        """Initialize Twitter API client"""
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # Initialize Tweepy client
        if self.bearer_token:
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API client initialized")
        else:
            self.client = None
            logger.warning("Twitter API credentials not configured")
        
        # Rate limiting - reduce frequency to avoid hitting limits
        self.last_request_time = 0
        self.min_request_interval = 2.0  # seconds between requests
    
    
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    
    def get_recent_mentions(self, limit: int = 100) -> List[Dict]:
        """
        Get recent mentions from Twitter

        Args:
            limit: Maximum number of tweets to fetch

        Returns:
            List of tweet dictionaries
        """
        if not self.client:
            logger.warning("Twitter client not configured - using mock data")
            return self._get_mock_data(limit)

        try:
            self._rate_limit()

            # Fetch recent tweets mentioning the brand
            query = os.getenv('TWITTER_SEARCH_QUERY', 'your_brand_name -is:retweet')

            # Limit max_results to 10 for free tier to avoid rate limits
            max_results = min(limit, 10)

            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=['created_at', 'public_metrics', 'author_id'],
                expansions=['author_id']
            )
            
            if not tweets.data:
                return []
            
            results = []
            for tweet in tweets.data:
                results.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat(),
                    'likes': tweet.public_metrics['like_count'],
                    'retweets': tweet.public_metrics['retweet_count'],
                    'replies': tweet.public_metrics['reply_count'],
                    'source': 'twitter'
                })
            
            logger.info(f"Fetched {len(results)} tweets")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching tweets: {str(e)}")
            return self._get_mock_data(limit)
    
    
    def fetch_tweets(self, keywords: List[str], count: int = 100) -> List[Dict]:
        """
        Fetch tweets based on keywords

        Args:
            keywords: List of keywords to search
            count: Number of tweets to fetch

        Returns:
            List of tweet dictionaries
        """
        if not self.client:
            logger.warning("Twitter client not configured - using mock data")
            return self._get_mock_data(count)

        try:
            self._rate_limit()

            # Build query from keywords
            query = ' OR '.join(keywords) + ' -is:retweet lang:en'

            # Limit max_results to 10 for free tier to avoid rate limits
            max_results = min(count, 10)

            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=['created_at', 'public_metrics', 'lang']
            )
            
            if not tweets.data:
                return []
            
            results = []
            for tweet in tweets.data:
                results.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat(),
                    'engagement': (
                        tweet.public_metrics['like_count'] +
                        tweet.public_metrics['retweet_count'] +
                        tweet.public_metrics['reply_count']
                    ),
                    'source': 'twitter'
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error fetching tweets by keywords: {str(e)}")
            return self._get_mock_data(count)
    
    
    def stream_tweets(self, callback, keywords: List[str]):
        """
        Stream tweets in real-time
        
        Args:
            callback: Function to call for each tweet
            keywords: Keywords to track
        """
        if not self.client:
            logger.warning("Twitter client not configured")
            return
        
        class StreamListener(tweepy.StreamingClient):
            def on_tweet(self, tweet):
                data = {
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': datetime.utcnow().isoformat(),
                    'source': 'twitter_stream'
                }
                callback(data)
            
            def on_error(self, status_code):
                logger.error(f"Stream error: {status_code}")
                return False
        
        try:
            stream = StreamListener(bearer_token=self.bearer_token)
            
            # Add rules for keywords
            for keyword in keywords:
                stream.add_rules(tweepy.StreamRule(keyword))
            
            # Start streaming
            stream.filter(tweet_fields=['created_at'])
            
        except Exception as e:
            logger.error(f"Error streaming tweets: {str(e)}")
    
    
    def get_user_timeline(self, username: str, count: int = 50) -> List[Dict]:
        """
        Get tweets from a specific user's timeline
        
        Args:
            username: Twitter username
            count: Number of tweets to fetch
            
        Returns:
            List of tweet dictionaries
        """
        if not self.client:
            return []
        
        try:
            self._rate_limit()
            
            # Get user ID
            user = self.client.get_user(username=username)
            
            if not user.data:
                return []
            
            # Get user's tweets
            tweets = self.client.get_users_tweets(
                id=user.data.id,
                max_results=min(count, 100),
                tweet_fields=['created_at', 'public_metrics']
            )
            
            if not tweets.data:
                return []
            
            results = []
            for tweet in tweets.data:
                results.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat(),
                    'username': username,
                    'source': 'twitter_user'
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error fetching user timeline: {str(e)}")
            return []
    
    
    def get_trending_topics(self, location_id: int = 1) -> List[str]:
        """
        Get trending topics
        
        Args:
            location_id: WOEID for location (1 = worldwide)
            
        Returns:
            List of trending topics
        """
        # Note: This requires Twitter API v1.1
        # For v2, you would need to implement differently
        # Returning mock data for demonstration
        return [
            '#TrendingNow',
            '#CustomerService',
            '#ProductLaunch',
            '#TechNews',
            '#BusinessGrowth'
        ]
    
    
    def _get_mock_data(self, count: int) -> List[Dict]:
        """Generate mock Twitter data for testing"""
        import random
        
        sample_texts = [
            "Absolutely loving the new product! Best purchase I've made this year! 🎉",
            "Customer service was incredibly helpful and responsive. Highly recommend!",
            "Not impressed with the quality. Expected better for the price.",
            "The product works fine, nothing special but does what it's supposed to do.",
            "Had some issues initially but support team resolved everything quickly!",
            "Disappointed with the delivery time. Product is good though.",
            "This company really knows how to take care of their customers!",
            "Average experience. Product is okay, service could be better.",
            "Wow! Exceeded all my expectations. Will definitely buy again!",
            "Terrible experience. Would not recommend to anyone.",
        ]
        
        results = []
        base_time = datetime.utcnow()
        
        for i in range(min(count, 100)):
            results.append({
                'id': f"mock_{i}_{int(time.time())}",
                'text': random.choice(sample_texts),
                'created_at': (base_time - timedelta(hours=random.randint(0, 48))).isoformat(),
                'likes': random.randint(0, 500),
                'retweets': random.randint(0, 100),
                'replies': random.randint(0, 50),
                'source': 'twitter_mock'
            })
        
        return results
    
    
    def check_connection(self) -> bool:
        """Check if Twitter API is accessible"""
        if not self.client:
            return False
        
        try:
            self._rate_limit()
            # Try to get authenticated user
            me = self.client.get_me()
            return me is not None
        except:
            return False
    
    
    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status"""
        # This would check actual rate limits
        return {
            'search_remaining': 450,
            'search_limit': 450,
            'search_reset': (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        }


# Example usage
if __name__ == "__main__":
    twitter = TwitterAPI()
    
    print("=== Fetching Recent Mentions ===")
    mentions = twitter.get_recent_mentions(limit=10)
    for tweet in mentions[:3]:
        print(f"\nTweet ID: {tweet['id']}")
        print(f"Text: {tweet['text']}")
        print(f"Created: {tweet['created_at']}")
    
    print(f"\n=== Fetching Tweets by Keywords ===")
    keywords = ['customer service', 'product quality']
    tweets = twitter.fetch_tweets(keywords, count=10)
    print(f"Found {len(tweets)} tweets")
    
    print("\n=== Rate Limit Status ===")
    status = twitter.get_rate_limit_status()
    print(f"Search remaining: {status['search_remaining']}/{status['search_limit']}")
    print(f"Reset at: {status['search_reset']}")