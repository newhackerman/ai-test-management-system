"""Framework settings (env-overridable). No secrets are committed here.

Adaptation points for a new project (change these, nothing else, to boot):
  QA_BASE_URL       backend base URL, e.g. http://127.0.0.1:8000
  QA_FRONTEND_URL   frontend base URL, e.g. http://localhost:3000
  QA_ADMIN_USER / QA_ADMIN_PASSWORD   login credentials for the test account
  QA_LOGIN_PATH     login endpoint, default /api/v1/auth/login
  QA_HEALTH_PATH    health endpoint, default /api/v1/health
  QA_TIMEOUT        request timeout in seconds, default 15
"""
import os

BASE_URL = os.environ.get("QA_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
FRONTEND_URL = os.environ.get("QA_FRONTEND_URL", "http://localhost:3000").rstrip("/")
ADMIN_USER = os.environ.get("QA_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("QA_ADMIN_PASSWORD", "admin")
LOGIN_PATH = os.environ.get("QA_LOGIN_PATH", "/api/v1/auth/login")
HEALTH_PATH = os.environ.get("QA_HEALTH_PATH", "/api/v1/health")
TIMEOUT = float(os.environ.get("QA_TIMEOUT", "15"))
