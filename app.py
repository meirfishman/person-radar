"""
Flask web application for Person Radar dashboard.
"""

import os
import json
from flask import Flask, render_template, jsonify, request
from src.utils import database

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


def load_config() -> dict:
    """Load configuration from config.json."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'people': [], 'settings': {}}


@app.route('/')
def dashboard():
    """Render the main dashboard."""
    config = load_config()
    people = config.get('people', [])
    return render_template('dashboard.html', people=people)


@app.route('/api/content')
def get_content():
    """Get all content grouped by person."""
    days = request.args.get('days', 7, type=int)
    include_viewed = request.args.get('include_viewed', 'true').lower() == 'true'

    # Ensure database is initialized
    database.init_database()

    content = database.get_all_content(days=days, include_viewed=include_viewed)

    # Group by person
    grouped = {}
    for item in content:
        person = item['person_name']
        if person not in grouped:
            grouped[person] = []
        # Convert datetime objects to strings for JSON
        if item.get('date_found'):
            item['date_found'] = str(item['date_found'])
        if item.get('date_published'):
            item['date_published'] = str(item['date_published'])
        grouped[person].append(item)

    return jsonify(grouped)


@app.route('/api/content/<int:content_id>/viewed', methods=['POST'])
def mark_viewed(content_id):
    """Mark a content item as viewed."""
    database.init_database()
    success = database.mark_as_viewed(content_id)
    return jsonify({'success': success})


@app.route('/api/content/<int:content_id>/unviewed', methods=['POST'])
def mark_unviewed(content_id):
    """Mark a content item as not viewed."""
    database.init_database()
    success = database.mark_as_unviewed(content_id)
    return jsonify({'success': success})


@app.route('/api/stats')
def get_stats():
    """Get database statistics."""
    database.init_database()
    stats = database.get_stats()
    return jsonify(stats)


@app.route('/api/people')
def get_people():
    """Get list of tracked people."""
    config = load_config()
    return jsonify(config.get('people', []))


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Trigger a data refresh (runs the update script)."""
    try:
        from src.update import run_update
        results = run_update()
        return jsonify({
            'success': True,
            'new_items': sum(results.values()),
            'details': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Initialize database on startup
    database.init_database()

    # Run Flask development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
