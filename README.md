# Person Radar

A web application that tracks updates from specific people you follow across YouTube, Twitter/X, and web news.

## Features

- **Multi-source tracking**: Monitors YouTube videos, Twitter posts, and news articles
- **Quality filtering**: Automatically filters out clickbait, reaction videos, and low-quality content
- **Clean dashboard**: Simple, minimal web interface to view and manage updates
- **Mark as viewed**: Track what you've already seen
- **Scheduled updates**: Run hourly to catch new content

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit `config.json` and add your API keys:

```json
{
  "api_keys": {
    "youtube": "YOUR_YOUTUBE_API_KEY",
    "twitter_bearer": "YOUR_TWITTER_BEARER_TOKEN",
    "newsapi": "YOUR_NEWSAPI_KEY"
  }
}
```

**Getting API Keys:**

- **YouTube Data API v3**:
  1. Go to [Google Cloud Console](https://console.cloud.google.com/)
  2. Create a project and enable YouTube Data API v3
  3. Create credentials (API key)
  4. Free tier: 10,000 units/day

- **Twitter API**:
  1. Apply at [Twitter Developer Portal](https://developer.twitter.com/)
  2. Create a project and get Bearer Token
  3. Free tier: Limited access

- **NewsAPI**:
  1. Register at [NewsAPI.org](https://newsapi.org/)
  2. Get your API key
  3. Free tier: 100 requests/day

### 3. Add People to Track

Edit `config.json` to add/modify the people you want to track:

```json
{
  "people": [
    {
      "name": "Person Name",
      "description": "Short description",
      "search_terms": ["Person Name", "alternate name"],
      "twitter_handle": "username",
      "youtube_channels": ["channel_id"]
    }
  ]
}
```

### 4. Run Initial Update

```bash
python -m src.update
```

### 5. Start the Dashboard

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## Scheduled Updates

### Using Cron (Linux/Mac)

Add to crontab (`crontab -e`):

```bash
# Run every hour
0 * * * * cd /path/to/person-radar && /path/to/python -m src.update >> /path/to/person-radar/data/cron.log 2>&1
```

### Using Task Scheduler (Windows)

Create a scheduled task to run:
```
python -m src.update
```

## Project Structure

```
person-radar/
├── app.py                 # Flask web application
├── config.json            # Configuration (people, API keys)
├── requirements.txt       # Python dependencies
├── src/
│   ├── checkers/          # Source checkers
│   │   ├── youtube.py     # YouTube video search
│   │   ├── twitter.py     # Twitter/X posts
│   │   └── news.py        # News articles
│   ├── utils/
│   │   ├── database.py    # SQLite database handler
│   │   └── quality_filter.py  # Content quality filtering
│   └── update.py          # Main update script
├── static/
│   ├── style.css          # Dashboard styles
│   └── script.js          # Dashboard JavaScript
├── templates/
│   └── dashboard.html     # Dashboard template
└── data/
    └── radar.db           # SQLite database (auto-created)
```

## Configuration Options

In `config.json` under `settings`:

| Option | Default | Description |
|--------|---------|-------------|
| `max_results_per_source` | 10 | Max items to fetch per source |
| `days_to_keep` | 7 | Days to display in dashboard |
| `quality_threshold` | 0.5 | Minimum quality score (0-1) |
| `update_interval_hours` | 1 | Recommended update frequency |

## Quality Filter

The quality filter automatically scores content based on:

- **Blacklist patterns**: Clickbait phrases, reaction videos, etc.
- **Whitelist patterns**: Interviews, podcasts, conferences
- **Source reputation**: Trusted vs untrusted channels
- **Content characteristics**: Title length, caps, emojis

Content below the quality threshold is filtered out.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/api/content` | GET | Get all content (params: `days`, `include_viewed`) |
| `/api/content/{id}/viewed` | POST | Mark item as viewed |
| `/api/content/{id}/unviewed` | POST | Mark item as unviewed |
| `/api/stats` | GET | Get statistics |
| `/api/refresh` | POST | Trigger data refresh |

## Troubleshooting

**No content appearing?**
- Check that API keys are configured correctly
- Run `python -m src.update` manually and check for errors
- Verify the database exists in `data/radar.db`

**API errors?**
- YouTube: Check quota at Google Cloud Console
- Twitter: Verify bearer token is valid
- NewsAPI: Check daily limit (100/day on free tier)

**Database issues?**
- Delete `data/radar.db` and run update again to recreate

## License

MIT
