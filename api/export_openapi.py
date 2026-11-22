"""Write the OpenAPI document the UI's types are generated from: python export_openapi.py > openapi.json"""

import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENV_FILE", "/nonexistent")

from app.main import app  # noqa: E402

print(json.dumps(app.openapi(), indent=1))
