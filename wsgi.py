import os
import sys
from pathlib import Path

# Ensure project root is on Python module search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env configuration if present
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app import create_app

app = create_app()
application = app  # WSGI entrypoint for PythonAnywhere, Gunicorn, uWSGI, Render

with app.app_context():
    from app.models.user import User
    try:
        if User.query.count() == 0:
            from app.services.fixtures import provision_synthetic_fixtures
            provision_synthetic_fixtures(app)
    except Exception:
        pass

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    app.run(host=host, port=port)

