import os
import sys
from app import create_app
from app.extensions import db
from waitress import serve

app = create_app()

with app.app_context():
    # Safely ensure SQLite parent directory exists before table creation
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"):
        sqlite_file = db_uri.replace("sqlite:///", "")
        if sqlite_file and not sqlite_file.startswith(":memory:"):
            db_dir = os.path.dirname(os.path.abspath(sqlite_file))
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

    # Initialize missing schema tables safely without resetting data
    db.create_all()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    print("=" * 65)
    print(" * Starting CampusVoice production server with Waitress")
    print(f" * Binding to: http://{host}:{port}")
    print(f" * Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f" * Upload folder: {app.config.get('UPLOAD_FOLDER')}")
    print("=" * 65)
    serve(app, host=host, port=port, threads=4)
