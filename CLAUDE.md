# Person Radar

## Overview
Person Radar is a web application that tracks updates from specific people you follow across multiple platforms. It aggregates content from YouTube, Twitter/X, and web news to provide a unified dashboard of recent activities from thought leaders and notable figures.

## Architecture

```
person-radar/
├── CLAUDE.md              # This file - project documentation
├── README.md              # Setup and usage instructions
├── requirements.txt       # Python dependencies
├── config.json            # Configuration: people to track, API keys
├── src/
│   ├── __init__.py
│   ├── checkers/          # Content source checkers
│   │   ├── __init__.py
│   │   ├── youtube.py     # YouTube video checker
│   │   ├── twitter.py     # Twitter/X checker
│   │   └── news.py        # Web news checker
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── database.py    # SQLite database handler
│   │   └── quality_filter.py  # Content quality filtering
│   └── update.py          # Main update script
├── app.py                 # Flask web application
├── static/
│   ├── style.css          # Dashboard styles
│   └── script.js          # Dashboard JavaScript
├── templates/
│   └── dashboard.html     # Main dashboard template
└── data/
    └── radar.db           # SQLite database (created at runtime)
```

## Key Components

### Database Schema (SQLite)
- **content** table: Stores all tracked content
  - id: Primary key
  - person_name: Name of the tracked person
  - content_type: 'youtube', 'twitter', or 'news'
  - title: Content title
  - url: Link to content
  - description: Brief description/snippet
  - date_found: When content was discovered
  - date_published: When content was published (if available)
  - viewed: Boolean flag for marking as read
  - quality_score: Numeric quality rating

### Checkers
Each checker module implements a `check(person_name, search_terms)` function that returns a list of content items.

### Quality Filter
Filters out low-quality content using:
- Keyword blacklist (clickbait, reaction videos, etc.)
- Source reputation scoring
- Title pattern matching

### Web Dashboard
- Flask backend serving API endpoints
- Simple HTML/CSS/JS frontend
- Real-time marking of items as viewed

## API Keys Required
- YouTube Data API v3 (free tier: 10,000 units/day)
- Twitter API (optional - uses web scraping fallback)
- NewsAPI.org (free tier: 100 requests/day)

## Running the Application
1. Install dependencies: `pip install -r requirements.txt`
2. Configure `config.json` with API keys
3. Run update script: `python -m src.update`
4. Start dashboard: `python app.py`
5. Open http://localhost:5000

## Scheduled Updates
Use cron or similar to run `python -m src.update` hourly:
```
0 * * * * cd /path/to/person-radar && python -m src.update
```

## Development Notes
- All times stored in UTC
- Database uses WAL mode for better concurrency
- Content older than 7 days is auto-archived (not deleted)
