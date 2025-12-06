"""
YouTube checker for Person Radar.
Searches YouTube for videos featuring tracked people.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
import logging

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False

logger = logging.getLogger(__name__)


class YouTubeChecker:
    """Check YouTube for videos featuring tracked people."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube checker.

        Args:
            api_key: YouTube Data API key. If not provided, will try to load from config.
        """
        self.api_key = api_key
        self.youtube = None

        if not YOUTUBE_API_AVAILABLE:
            logger.warning("google-api-python-client not installed. YouTube checking disabled.")
            return

        if not self.api_key:
            self.api_key = self._load_api_key()

        if self.api_key and self.api_key != 'YOUR_YOUTUBE_API_KEY':
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API: {e}")

    def _load_api_key(self) -> Optional[str]:
        """Load API key from config file."""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get('api_keys', {}).get('youtube')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load config: {e}")
            return None

    def search_videos(
        self,
        person_name: str,
        search_terms: Optional[list[str]] = None,
        max_results: int = 10,
        days_back: int = 7
    ) -> list[dict]:
        """
        Search YouTube for videos featuring a person.

        Args:
            person_name: Name of the person to search for
            search_terms: Additional search terms (defaults to person_name)
            max_results: Maximum number of results to return
            days_back: How many days back to search

        Returns:
            List of video dictionaries with title, url, description, etc.
        """
        if not self.youtube:
            logger.warning("YouTube API not available, using fallback")
            return self._fallback_search(person_name, search_terms)

        results = []
        terms = search_terms or [person_name]

        # Calculate date range
        published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'

        for term in terms:
            try:
                search_response = self.youtube.search().list(
                    q=f'"{term}" interview OR podcast OR talk OR keynote',
                    part='id,snippet',
                    maxResults=max_results,
                    type='video',
                    publishedAfter=published_after,
                    order='date',
                    relevanceLanguage='en',
                    videoDuration='medium'  # Filter out shorts (< 4 min)
                ).execute()

                for item in search_response.get('items', []):
                    video_id = item['id']['videoId']
                    snippet = item['snippet']

                    video_data = {
                        'person_name': person_name,
                        'content_type': 'youtube',
                        'title': snippet['title'],
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'description': snippet.get('description', ''),
                        'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                        'date_published': self._parse_date(snippet.get('publishedAt')),
                        'source_channel': snippet.get('channelTitle', '')
                    }

                    # Avoid duplicates
                    if not any(r['url'] == video_data['url'] for r in results):
                        results.append(video_data)

            except HttpError as e:
                logger.error(f"YouTube API error for '{term}': {e}")
            except Exception as e:
                logger.error(f"Error searching YouTube for '{term}': {e}")

        return results

    def get_channel_videos(
        self,
        channel_id: str,
        person_name: str,
        max_results: int = 10,
        days_back: int = 7
    ) -> list[dict]:
        """
        Get recent videos from a specific channel.

        Args:
            channel_id: YouTube channel ID
            person_name: Name of the person (for attribution)
            max_results: Maximum number of results
            days_back: How many days back to search

        Returns:
            List of video dictionaries
        """
        if not self.youtube:
            return []

        results = []
        published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'

        try:
            search_response = self.youtube.search().list(
                channelId=channel_id,
                part='id,snippet',
                maxResults=max_results,
                type='video',
                publishedAfter=published_after,
                order='date'
            ).execute()

            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']

                results.append({
                    'person_name': person_name,
                    'content_type': 'youtube',
                    'title': snippet['title'],
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'description': snippet.get('description', ''),
                    'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                    'date_published': self._parse_date(snippet.get('publishedAt')),
                    'source_channel': snippet.get('channelTitle', '')
                })

        except HttpError as e:
            logger.error(f"YouTube API error for channel {channel_id}: {e}")
        except Exception as e:
            logger.error(f"Error fetching channel videos: {e}")

        return results

    def _fallback_search(
        self,
        person_name: str,
        search_terms: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Fallback search when API is not available.
        Returns empty list - in production, could use web scraping.
        """
        logger.info(f"Fallback search for {person_name} - no results (API key required)")
        return []

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string to datetime."""
        if not date_str:
            return None
        try:
            # Handle YouTube's ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None


def check(
    person_name: str,
    search_terms: Optional[list[str]] = None,
    youtube_channels: Optional[list[str]] = None,
    api_key: Optional[str] = None,
    max_results: int = 10,
    days_back: int = 7
) -> list[dict]:
    """
    Main entry point for YouTube checking.

    Args:
        person_name: Name of the person to search for
        search_terms: Additional search terms
        youtube_channels: List of channel IDs to check
        api_key: YouTube API key
        max_results: Maximum results per search
        days_back: Days to look back

    Returns:
        List of content items found
    """
    checker = YouTubeChecker(api_key)
    results = []

    # Search for videos mentioning the person
    search_results = checker.search_videos(
        person_name=person_name,
        search_terms=search_terms,
        max_results=max_results,
        days_back=days_back
    )
    results.extend(search_results)

    # Check specific channels if provided
    if youtube_channels:
        for channel_id in youtube_channels:
            channel_results = checker.get_channel_videos(
                channel_id=channel_id,
                person_name=person_name,
                max_results=max_results,
                days_back=days_back
            )
            # Add only non-duplicate results
            for item in channel_results:
                if not any(r['url'] == item['url'] for r in results):
                    results.append(item)

    return results


if __name__ == '__main__':
    # Test the YouTube checker
    logging.basicConfig(level=logging.INFO)

    results = check(
        person_name='Andrej Karpathy',
        search_terms=['Andrej Karpathy'],
        days_back=30
    )

    print(f"Found {len(results)} videos:")
    for r in results[:5]:
        print(f"  - {r['title'][:60]}...")
        print(f"    {r['url']}")
