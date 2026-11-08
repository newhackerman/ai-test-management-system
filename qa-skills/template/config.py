"""Framework settings (env-overridable). No secrets are committed here.

Adaptation points for a new project (change these, nothing else, to boot):
  QA_BASE_URL       backend base URL, e.g. http://127.0.0.1:8000
  QA_FRONTEND_URL   frontend base URL, e.g. http://localhost:3000
  QA_ADMIN_USER / QA_ADMIN_PASSWORD   login credentials for the test account
  QA_LOGIN_PATH     login endpoint, default /api/v1/auth/login
  QA_LOGOUT_PATH    logout endpoint, default /api/v1/auth/logout
  QA_HEALTH_PATH    health endpoint, default /api/v1/health
  QA_TIMEOUT        request timeout in seconds, default 15
  QA_AUTH_SCHEME    bearer (default) / cookie / apikey
                    bearer: login returns a token, sent as
                    Authorization: Bearer <token>.
                    cookie: login sets a session cookie; httpx keeps it
                    in its cookie jar, no header is sent.
                    apikey: every request sends QA_API_KEY_HEADER:
                    QA_API_KEY (no login call).
                    basic auth: not covered here — replace the login
                    call in conftest.py with a direct client instead.
  QA_TOKEN_FIELD    token field in the login response, default access_token.
                    Also checked inside a nested "data" object.
  QA_REFRESH_FIELD  refresh-token field, default refresh_token (empty
                    means the API returns no refresh token).
  QA_API_KEY_HEADER API-key header name, default X-API-Key (apikey only)
  QA_ENVELOPE       success (default) / code / bare
                    success: {"success": true, "<resource>": {...}}
                    code:    {"code": 0, "data": {...}, "message": ...}
                             (code 0 or 200 means success)
                    bare:    the body itself is the resource, no wrapper
  QA_HAS_OPENAPI    1 (default) when the backend serves an OpenAPI
                    document; 0 skips the docs/openapi smoke tests.
  QA_DOCS_PATH      API docs page, default /api/v1/docs
  QA_OPENAPI_PATH   OpenAPI JSON document, default /api/v1/openapi.json
  QA_APP_ROOT       frontend app container selector, default #root
                    (React). Vue apps use #app; set it per project.
"""
import os

BASE_URL = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_URL = os.environ.get("QA_FRONTEND_URL", "http://localhost:3000").rstrip("/")
ADMIN_USER = os.environ.get("QA_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("QA_ADMIN_PASSWORD", "admin")
LOGIN_PATH = os.environ.get("QA_LOGIN_PATH", "/api/v1/auth/login")
LOGOUT_PATH = os.environ.get("QA_LOGOUT_PATH", "/api/v1/auth/logout")
HEALTH_PATH = os.environ.get("QA_HEALTH_PATH", "/api/v1/health")
TIMEOUT = float(os.environ.get("QA_TIMEOUT", "15"))

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
