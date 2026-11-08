"""Framework settings (env-overridable). No secrets are committed here;
defaults are the local deployment's documented test credentials."""
import os

BASE_URL = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_URL = os.environ.get("QA_FRONTEND_URL", "http://localhost:3000").rstrip("/")
ADMIN_USER = os.environ.get("QA_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("QA_ADMIN_PASSWORD", "TEST@test1")
LOGIN_PATH = os.environ.get("QA_LOGIN_PATH", "/api/v1/auth/login")
LOGOUT_PATH = os.environ.get("QA_LOGOUT_PATH", "/api/v1/auth/logout")
HEALTH_PATH = os.environ.get("QA_HEALTH_PATH", "/api/v1/health")
TIMEOUT = float(os.environ.get("QA_TIMEOUT", "15"))

# Auth and envelope shape switches (template 2026-11-08 optimisation).
# This project uses the defaults: bearer auth, access_token top-level,
# success envelope, OpenAPI document served, React #root container.
AUTH_SCHEME = os.environ.get("QA_AUTH_SCHEME", "bearer").strip().lower()
TOKEN_FIELD = os.environ.get("QA_TOKEN_FIELD", "access_token")
REFRESH_FIELD = os.environ.get("QA_REFRESH_FIELD", "refresh_token")
API_KEY = os.environ.get("QA_API_KEY", "")
API_KEY_HEADER = os.environ.get("QA_API_KEY_HEADER", "X-API-Key")
ENVELOPE = os.environ.get("QA_ENVELOPE", "success").strip().lower()
HAS_OPENAPI = os.environ.get("QA_HAS_OPENAPI", "1") == "1"
DOCS_PATH = os.environ.get("QA_DOCS_PATH", "/api/v1/docs")
OPENAPI_PATH = os.environ.get("QA_OPENAPI_PATH", "/api/v1/openapi.json")
APP_ROOT = os.environ.get("QA_APP_ROOT", "#root")
