from ml_app import create_app
from ml_app.database import db

def main():
    """Initialize the database with schema."""
    app = create_app()
    with app.app_context():
        print("Initializing database...")
        db.init_db(force=True)
        print("Database initialization complete!")

if __name__ == '__main__':
    main()
