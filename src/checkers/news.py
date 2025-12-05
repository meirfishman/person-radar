"""
News checker for Person Radar.
Searches for news articles and interviews featuring tracked people.
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


class NewsChecker:
    """Check news sources for articles featuring tracked people."""

    NEWSAPI_BASE_URL = "https://newsapi.org/v2"

    # Domains known for quality tech/AI coverage
    QUALITY_DOMAINS = [
        'techcrunch.com',
        'wired.com',
        'theverge.com',
        'arstechnica.com',
        'technologyreview.com',
        'bloomberg.com',
        'reuters.com',
        'ft.com',
        'wsj.com',
        'nytimes.com',
        'washingtonpost.com',
        'bbc.com',
        'theguardian.com',
        'nature.com',
        'science.org',
        'forbes.com',
        'venturebeat.com',
        'zdnet.com',
        'cnet.com',
        'engadget.com',
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize News checker.

        Args:
            api_key: NewsAPI.org API key. If not provided, will try to load from config.
        """
        self.api_key = api_key

        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not installed. News checking disabled.")
            return

        if not self.api_key:
            self.api_key = self._load_api_key()

    def _load_api_key(self) -> Optional[str]:
        """Load API key from config file."""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('api_keys', {}).get('newsapi')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load config: {e}")
            return None

    def _is_key_valid(self) -> bool:
        """Check if API key is set and not a placeholder."""
        return (
            self.api_key is not None and
            self.api_key != 'YOUR_NEWSAPI_KEY' and
            len(self.api_key) > 10
        )

    def search_news(
        self,
        person_name: str,
        search_terms: Optional[list[str]] = None,
        max_results: int = 10,
        days_back: int = 7
    ) -> list[dict]:
        """
        Search for news articles about a person.

        Args:
            person_name: Name of the person to search for
            search_terms: Additional search terms
            max_results: Maximum number of results
            days_back: How many days back to search

        Returns:
            List of article dictionaries
        """
        if not self._is_key_valid():
            logger.warning("NewsAPI key not available, using fallback")
            return self._fallback_search(person_name, search_terms)

        results = []
        terms = search_terms or [person_name]
        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        for term in terms:
            try:
                # Use 'everything' endpoint for broader search
                url = f"{self.NEWSAPI_BASE_URL}/everything"
                params = {
                    'q': f'"{term}"',
                    'from': from_date,
                    'sortBy': 'publishedAt',
                    'language': 'en',
                    'pageSize': max_results,
                    'apiKey': self.api_key
                }

                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if data.get('status') != 'ok':
                    logger.error(f"NewsAPI error: {data.get('message')}")
                    continue

                for article in data.get('articles', []):
                    # Skip if URL already in results
                    article_url = article.get('url', '')
                    if any(r['url'] == article_url for r in results):
                        continue

                    source_name = article.get('source', {}).get('name', 'Unknown')

                    results.append({
                        'person_name': person_name,
                        'content_type': 'news',
                        'title': article.get('title', ''),
                        'url': article_url,
                        'description': article.get('description', ''),
                        'thumbnail_url': article.get('urlToImage'),
                        'date_published': self._parse_date(article.get('publishedAt')),
                        'source_channel': source_name
                    })

            except requests.RequestException as e:
                logger.error(f"News API error for '{term}': {e}")
            except Exception as e:
                logger.error(f"Error searching news for '{term}': {e}")

        return results

    def search_quality_sources(
        self,
        person_name: str,
        search_terms: Optional[list[str]] = None,
        max_results: int = 10,
        days_back: int = 7
    ) -> list[dict]:
        """
        Search only quality news sources.

        Args:
            person_name: Name of the person to search for
            search_terms: Additional search terms
            max_results: Maximum number of results
            days_back: How many days back to search

        Returns:
            List of article dictionaries from quality sources
        """
        if not self._is_key_valid():
            return []

        results = []
        terms = search_terms or [person_name]
        from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        domains = ','.join(self.QUALITY_DOMAINS)

        for term in terms:
            try:
                url = f"{self.NEWSAPI_BASE_URL}/everything"
                params = {
                    'q': f'"{term}"',
                    'from': from_date,
                    'domains': domains,
                    'sortBy': 'publishedAt',
                    'language': 'en',
                    'pageSize': max_results,
                    'apiKey': self.api_key
                }

                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if data.get('status') != 'ok':
                    continue

                for article in data.get('articles', []):
                    article_url = article.get('url', '')
                    if any(r['url'] == article_url for r in results):
                        continue

                    source_name = article.get('source', {}).get('name', 'Unknown')

                    results.append({
                        'person_name': person_name,
                        'content_type': 'news',
                        'title': article.get('title', ''),
                        'url': article_url,
                        'description': article.get('description', ''),
                        'thumbnail_url': article.get('urlToImage'),
                        'date_published': self._parse_date(article.get('publishedAt')),
                        'source_channel': source_name
                    })

            except requests.RequestException as e:
                logger.error(f"News API error for '{term}': {e}")

        return results

    def _fallback_search(
        self,
        person_name: str,
        search_terms: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Fallback search when API is not available.
        Returns empty list - API key required for news search.
        """
        logger.info(f"News fallback for {person_name} - API key required")
        return []

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string to datetime."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try alternate format
                return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                return None


def check(
    person_name: str,
    search_terms: Optional[list[str]] = None,
    api_key: Optional[str] = None,
    max_results: int = 10,
    days_back: int = 7,
    quality_only: bool = True
) -> list[dict]:
    """
    Main entry point for news checking.

    Args:
        person_name: Name of the person to search for
        search_terms: Additional search terms
        api_key: NewsAPI.org API key
        max_results: Maximum results to return
        days_back: Days to look back
        quality_only: If True, only search quality sources

    Returns:
        List of content items found
    """
    checker = NewsChecker(api_key)

    if quality_only:
        return checker.search_quality_sources(
            person_name=person_name,
            search_terms=search_terms,
            max_results=max_results,
            days_back=days_back
        )
    else:
        return checker.search_news(
            person_name=person_name,
            search_terms=search_terms,
            max_results=max_results,
            days_back=days_back
        )


if __name__ == '__main__':
    # Test the news checker
    logging.basicConfig(level=logging.INFO)

    results = check(
        person_name='Demis Hassabis',
        search_terms=['Demis Hassabis', 'DeepMind'],
        days_back=7
    )

    print(f"Found {len(results)} articles:")
    for r in results[:5]:
        print(f"  - {r['title'][:60]}...")
        print(f"    {r['url']}")
        print(f"    Source: {r['source_channel']}")
