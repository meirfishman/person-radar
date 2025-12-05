"""
Main update script for Person Radar.
Fetches new content from all sources for all tracked people.
Run this script on a schedule (e.g., hourly via cron).
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.checkers import youtube, twitter, news
from src.utils import database, quality_filter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), '..', 'data', 'update.log'),
            mode='a'
        )
    ]
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from config.json."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        sys.exit(1)


def update_person(
    person: dict,
    api_keys: dict,
    settings: dict
) -> dict:
    """
    Fetch and store new content for a single person.

    Args:
        person: Person configuration dict
        api_keys: API keys dict
        settings: Settings dict

    Returns:
        Dict with counts of new items added per source
    """
    name = person['name']
    search_terms = person.get('search_terms', [name])
    twitter_handle = person.get('twitter_handle')
    youtube_channels = person.get('youtube_channels', [])

    max_results = settings.get('max_results_per_source', 10)
    days_back = settings.get('days_to_keep', 7)
    quality_threshold = settings.get('quality_threshold', 0.5)

    results = {
        'youtube': 0,
        'twitter': 0,
        'news': 0
    }

    logger.info(f"Checking updates for: {name}")

    # 1. Check YouTube
    try:
        youtube_items = youtube.check(
            person_name=name,
            search_terms=search_terms,
            youtube_channels=youtube_channels,
            api_key=api_keys.get('youtube'),
            max_results=max_results,
            days_back=days_back
        )

        # Filter for quality
        youtube_items = quality_filter.filter_content_list(
            youtube_items,
            threshold=quality_threshold
        )

        for item in youtube_items:
            added_id = database.add_content(
                person_name=item['person_name'],
                content_type=item['content_type'],
                title=item['title'],
                url=item['url'],
                description=item.get('description'),
                thumbnail_url=item.get('thumbnail_url'),
                date_published=item.get('date_published'),
                quality_score=item.get('quality_score', 0.5),
                source_channel=item.get('source_channel')
            )
            if added_id:
                results['youtube'] += 1
                logger.info(f"  [YouTube] Added: {item['title'][:50]}...")

    except Exception as e:
        logger.error(f"  [YouTube] Error: {e}")

    # 2. Check Twitter
    try:
        twitter_items = twitter.check(
            person_name=name,
            twitter_handle=twitter_handle,
            bearer_token=api_keys.get('twitter_bearer'),
            max_results=max_results,
            days_back=days_back
        )

        # Filter for quality (less strict for tweets)
        twitter_items = quality_filter.filter_content_list(
            twitter_items,
            threshold=max(0.3, quality_threshold - 0.2)
        )

        for item in twitter_items:
            added_id = database.add_content(
                person_name=item['person_name'],
                content_type=item['content_type'],
                title=item['title'],
                url=item['url'],
                description=item.get('description'),
                thumbnail_url=item.get('thumbnail_url'),
                date_published=item.get('date_published'),
                quality_score=item.get('quality_score', 0.5),
                source_channel=item.get('source_channel')
            )
            if added_id:
                results['twitter'] += 1
                logger.info(f"  [Twitter] Added: {item['title'][:50]}...")

    except Exception as e:
        logger.error(f"  [Twitter] Error: {e}")

    # 3. Check News
    try:
        news_items = news.check(
            person_name=name,
            search_terms=search_terms,
            api_key=api_keys.get('newsapi'),
            max_results=max_results,
            days_back=days_back,
            quality_only=True
        )

        # Filter for quality
        news_items = quality_filter.filter_content_list(
            news_items,
            threshold=quality_threshold
        )

        for item in news_items:
            added_id = database.add_content(
                person_name=item['person_name'],
                content_type=item['content_type'],
                title=item['title'],
                url=item['url'],
                description=item.get('description'),
                thumbnail_url=item.get('thumbnail_url'),
                date_published=item.get('date_published'),
                quality_score=item.get('quality_score', 0.5),
                source_channel=item.get('source_channel')
            )
            if added_id:
                results['news'] += 1
                logger.info(f"  [News] Added: {item['title'][:50]}...")

    except Exception as e:
        logger.error(f"  [News] Error: {e}")

    return results


def run_update(config: Optional[dict] = None) -> dict:
    """
    Run a full update for all tracked people.

    Args:
        config: Configuration dict (loads from file if not provided)

    Returns:
        Dict with total counts of new items added
    """
    if config is None:
        config = load_config()

    people = config.get('people', [])
    api_keys = config.get('api_keys', {})
    settings = config.get('settings', {})

    # Initialize database
    database.init_database()

    logger.info(f"Starting update for {len(people)} people...")
    start_time = datetime.now()

    totals = {
        'youtube': 0,
        'twitter': 0,
        'news': 0
    }

    for person in people:
        try:
            results = update_person(person, api_keys, settings)
            for key in totals:
                totals[key] += results[key]
        except Exception as e:
            logger.error(f"Error updating {person.get('name', 'unknown')}: {e}")

    # Cleanup old content
    days_to_keep = settings.get('days_to_keep', 7) * 3  # Keep 3x the display window
    deleted = database.cleanup_old_content(days=days_to_keep)
    if deleted > 0:
        logger.info(f"Cleaned up {deleted} old items")

    elapsed = (datetime.now() - start_time).total_seconds()
    total_added = sum(totals.values())

    logger.info(f"Update complete in {elapsed:.1f}s - Added {total_added} new items")
    logger.info(f"  YouTube: {totals['youtube']}, Twitter: {totals['twitter']}, News: {totals['news']}")

    return totals


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Update Person Radar database')
    parser.add_argument(
        '--person',
        help='Update only a specific person (by name)'
    )
    parser.add_argument(
        '--source',
        choices=['youtube', 'twitter', 'news'],
        help='Update only a specific source'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fetched without saving'
    )
    args = parser.parse_args()

    config = load_config()

    # Filter by person if specified
    if args.person:
        config['people'] = [
            p for p in config['people']
            if args.person.lower() in p['name'].lower()
        ]
        if not config['people']:
            logger.error(f"No person found matching: {args.person}")
            sys.exit(1)

    run_update(config)


if __name__ == '__main__':
    main()
