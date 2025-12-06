"""
Twitter/X checker for Person Radar.
Fetches recent tweets from tracked people.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
import logging

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class TwitterChecker:
    """Check Twitter/X for tweets from tracked people."""

    BASE_URL = "https://api.twitter.com/2"

    def __init__(self, bearer_token: Optional[str] = None):
        """
        Initialize Twitter checker.

        Args:
            bearer_token: Twitter API bearer token. If not provided, will try to load from config.
        """
        self.bearer_token = bearer_token

        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not installed. Twitter checking disabled.")
            return

        if not self.bearer_token:
            self.bearer_token = self._load_bearer_token()

    def _load_bearer_token(self) -> Optional[str]:
        """Load bearer token from config file."""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('api_keys', {}).get('twitter_bearer')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load config: {e}")
            return None

    def _get_headers(self) -> dict:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "PersonRadar/1.0"
        }

    def _is_token_valid(self) -> bool:
        """Check if bearer token is set and not a placeholder."""
        return (
            self.bearer_token is not None and
            self.bearer_token != 'YOUR_TWITTER_BEARER_TOKEN' and
            len(self.bearer_token) > 20
        )

    def get_user_id(self, username: str) -> Optional[str]:
        """
        Get Twitter user ID from username.

        Args:
            username: Twitter handle (without @)

        Returns:
            User ID string or None if not found
        """
        if not self._is_token_valid():
            return None

        url = f"{self.BASE_URL}/users/by/username/{username}"

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('id')
        except requests.RequestException as e:
            logger.error(f"Failed to get user ID for @{username}: {e}")
            return None

    def get_user_tweets(
        self,
        username: str,
        person_name: str,
        max_results: int = 10,
        days_back: int = 7
    ) -> list[dict]:
        """
        Get recent tweets from a user.

        Args:
            username: Twitter handle (without @)
            person_name: Full name for attribution
            max_results: Maximum number of tweets to fetch
            days_back: How many days back to search

        Returns:
            List of tweet dictionaries
        """
        if not self._is_token_valid():
            logger.warning("Twitter API token not available, using fallback")
            return self._fallback_search(username, person_name)

        user_id = self.get_user_id(username)
        if not user_id:
            logger.warning(f"Could not find user ID for @{username}")
            return []

        results = []
        start_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'

        url = f"{self.BASE_URL}/users/{user_id}/tweets"
        params = {
            'max_results': min(max_results, 100),  # Twitter API max is 100
            'start_time': start_time,
            'tweet.fields': 'created_at,public_metrics,text',
            'expansions': 'attachments.media_keys',
            'media.fields': 'url,preview_image_url'
        }

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            for tweet in data.get('data', []):
                tweet_id = tweet['id']
                text = tweet.get('text', '')

                # Skip retweets (they start with "RT @")
                if text.startswith('RT @'):
                    continue

                # Skip replies (unless they're threads from the same user)
                if text.startswith('@') and not text.startswith(f'@{username}'):
                    continue

                results.append({
                    'person_name': person_name,
                    'content_type': 'twitter',
                    'title': self._truncate_text(text, 100),
                    'url': f'https://twitter.com/{username}/status/{tweet_id}',
                    'description': text,
                    'thumbnail_url': None,
                    'date_published': self._parse_date(tweet.get('created_at')),
                    'source_channel': f'@{username}'
                })

        except requests.RequestException as e:
            logger.error(f"Failed to get tweets for @{username}: {e}")

        return results

    def _fallback_search(self, username: str, person_name: str) -> list[dict]:
        """
        Fallback when API is not available.
        Returns a placeholder indicating Twitter needs to be checked manually.
        """
        logger.info(f"Twitter fallback for @{username} - API token required for full functionality")
        return []

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length, adding ellipsis if needed."""
        text = text.replace('\n', ' ').strip()
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + '...'

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string to datetime."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None


def check(
    person_name: str,
    twitter_handle: Optional[str] = None,
    bearer_token: Optional[str] = None,
    max_results: int = 10,
    days_back: int = 7
) -> list[dict]:
    """
    Main entry point for Twitter checking.

    Args:
        person_name: Name of the person
        twitter_handle: Twitter username (without @)
        bearer_token: Twitter API bearer token
        max_results: Maximum results to return
        days_back: Days to look back

    Returns:
        List of content items found
    """
    if not twitter_handle:
        logger.info(f"No Twitter handle configured for {person_name}")
        return []

    checker = TwitterChecker(bearer_token)

    return checker.get_user_tweets(
        username=twitter_handle,
        person_name=person_name,
        max_results=max_results,
        days_back=days_back
    )


if __name__ == '__main__':
    # Test the Twitter checker
    logging.basicConfig(level=logging.INFO)

    results = check(
        person_name='Andrej Karpathy',
        twitter_handle='karpathy',
        days_back=7
    )

    print(f"Found {len(results)} tweets:")
    for r in results[:5]:
        print(f"  - {r['title']}")
        print(f"    {r['url']}")
