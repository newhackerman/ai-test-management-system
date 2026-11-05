"""Framework settings (env-overridable). No secrets are committed here;
defaults are the local deployment's documented test credentials."""
import os

BASE_URL = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_USER = os.environ.get("QA_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("QA_ADMIN_PASSWORD", "TEST@test1")
TIMEOUT = float(os.environ.get("QA_TIMEOUT", "15"))
