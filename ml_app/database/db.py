import sqlite3
import click
from flask import current_app, g
from datetime import datetime
from flask.cli import with_appcontext
import os

def adapt_datetime(dt):
    """Convert datetime to string."""
    return dt.isoformat()

def convert_datetime(s):
    """Convert string to datetime."""
    try:
        return datetime.fromisoformat(s.decode())
    except (AttributeError, ValueError):
        return None

def get_db():
    """Get database connection."""
    if 'db' not in g:
        # Register timestamp converter
        sqlite3.register_adapter(datetime, adapt_datetime)
        sqlite3.register_converter('timestamp', convert_datetime)
        
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        g.db.row_factory = sqlite3.Row
    
    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    
    if db is not None:
        db.close()

def init_db(force=False):
    """Initialize database."""
    # Check if database file exists
    if force or not os.path.exists(current_app.config['DATABASE']):
        db = get_db()
        with current_app.open_resource('database/schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        db.commit()

@click.command('init-db')
@click.option('--force', is_flag=True, help='Force reinitialize the database even if it exists')
@with_appcontext
def init_db_command(force):
    """Clear the existing data and create new tables."""
    init_db(force)
    click.echo('Initialized the database.')

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
