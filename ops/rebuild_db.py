#!/usr/bin/env python3
"""Rebuild the ai-test-management-system database from scratch.

Usage (called by ops/recover.sh, or manually):
    backend/venv/bin/python ops/rebuild_db.py

What it does, idempotently:
  1. Creates all tables from the SQLAlchemy models WITH FOREIGN KEY
     constraints kept. (Before round 5 / U1 the FKs were stripped here
     because 39 INT-vs-BIGINT FK mismatches made MySQL reject create_all
     with FKs, error 3780. The mismatches are fixed, verified on a scratch
     database: 111 tables, 158 FK constraints.)
  2. Seeds default permissions + roles via PermissionService.
  3. Creates the admin user (username ``admin``) if missing and links
     it to the ``admin`` role.

Configuration comes from backend/.env (DATABASE_URL), loaded by the
app's pydantic settings -- no credentials are stored in this file.
The admin password is the deployment default used by the test suite;
it is passed via the ADMIN_PASSWORD environment variable and defaults
to the documented default only when the variable is absent.
"""

import os
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from sqlalchemy import inspect  # noqa: E402

from src.core.config import settings  # noqa: E402
from src.core.database import SessionLocal, engine  # noqa: E402
import src.models  # noqa: E402,F401  (import registers every model)
import src.models.audit  # noqa: E402,F401  (register audit_logs/security_events)
import src.models.dashboard  # noqa: E402,F401  (register 6 dashboard tables)
from src.models.base import Base  # noqa: E402
from src.models.permission import Permission  # noqa: E402
from src.models.role import Role  # noqa: E402
from src.models.user import User, UserRole, UserStatus  # noqa: E402
from src.services.permission import PermissionService  # noqa: E402
from src.utils.password import password_service  # noqa: E402

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "TEST@test1")


def create_tables() -> None:
    # U1 fixed (round 5): all 39 FK type mismatches aligned, so create_all
    # runs with FOREIGN KEY constraints kept (verified on a scratch
    # database: 111 tables, 158 FK constraints).
    print("creating tables (FK constraints kept)...")
    Base.metadata.create_all(bind=engine)
    names = sorted(inspect(engine).get_table_names())
    print(f"tables present after create_all: {len(names)}")


def seed_permissions_and_roles(db) -> None:
    service = PermissionService(db)
    before_p = db.query(Permission).count()
    before_r = db.query(Role).count()
    service.initialize_default_roles()
    after_p = db.query(Permission).count()
    after_r = db.query(Role).count()
    print(f"permissions: {before_p} -> {after_p}, roles: {before_r} -> {after_r}")


def seed_admin(db) -> None:
    existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if existing:
        print("admin user already exists, skipping")
        return
    salt, password_hash = password_service.hash_password(ADMIN_PASSWORD)
    admin = User(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password_hash=password_hash,
        salt=salt,
        nickname="系统管理员",
        status=UserStatus.ACTIVE,
        is_active=True,
        is_superuser=True,
        is_email_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    role = db.query(Role).filter(Role.code == "admin").first()
    if role is not None:
        db.add(UserRole(user_id=admin.id, role_id=role.id))
        db.commit()
        print(f"admin user created (id={admin.id}) and linked to role 'admin'")
    else:
        print(f"admin user created (id={admin.id}); role 'admin' not found, skipped link")


def main() -> int:
    print(f"database: {settings.DATABASE_URL.split('@')[-1]}")
    create_tables()
    db = SessionLocal()
    try:
        seed_permissions_and_roles(db)
        seed_admin(db)
    finally:
        db.close()
    print("database rebuild done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
