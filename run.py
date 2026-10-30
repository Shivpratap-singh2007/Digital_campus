import os
import sys
from app import create_app
from app.extensions import db
from waitress import serve

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    print("=" * 65)
    print(f" * Starting CampusVoice production demo server with Waitress")
    print(f" * Serving at: http://{host}:{port}")
    print(f" * Environment: Flask 3.x, SQLite, Waitress, Bootstrap 5")
    print(f" * Press Ctrl+C to terminate.")
    print("=" * 65)
    serve(app, host=host, port=port, threads=4)
