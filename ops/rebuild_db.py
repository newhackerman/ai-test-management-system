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
    # 第 12 项：半建库自检——create_all 只建缺失的表，不修已存在
    # 的表；若某张表建表失败，数量会对不上，必须 loud fail 而不是
    # 静默继续去 seeding。
    expected = len(Base.metadata.tables)
    if len(names) != expected:
        missing = sorted(set(Base.metadata.tables) - set(names))
        raise SystemExit(
            f"create_all incomplete: {len(names)} tables present, "
            f"{expected} expected; missing: {missing}"
        )


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


def verify_seed(db) -> None:
    """第 12 项：种子自检——半建库（权限/角色只种了一部分）必须被
    发现，而不是静默当作成功。admin 角色必须持有全部权限的关联，
    否则管理员登录后处处 403。"""
    from sqlalchemy import func as _func
    from src.models.permission import RolePermission as _RP

    n_perm = db.query(Permission).count()
    n_role = db.query(Role).count()
    admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    admin_role = db.query(Role).filter(Role.code == "admin").first()
    problems = []
    if n_perm < 45:  # 种子权限数（见 PermissionService 种子列表）
        problems.append(f"permissions={n_perm} (< 45)")
    if n_role < 9:  # 种子角色数
        problems.append(f"roles={n_role} (< 9)")
    if admin is None:
        problems.append("admin user missing")
    if admin_role is None:
        problems.append("admin role missing")
    else:
        n_links = (
            db.query(_RP).filter(_RP.role_id == admin_role.id).count()
        )
        if n_links != n_perm:
            problems.append(
                f"admin role has {n_links} permission links, "
                f"want {n_perm} (== permissions)"
            )
        if admin is not None:
            linked = (
                db.query(UserRole)
                .filter(
                    UserRole.user_id == admin.id,
                    UserRole.role_id == admin_role.id,
                )
                .first()
            )
            if linked is None:
                problems.append("admin user not linked to admin role")
    if problems:
        raise SystemExit(f"seed verification failed: {'; '.join(problems)}")
    print(
        f"seed verified: permissions={n_perm}, roles={n_role}, "
        f"admin role links={n_links}"
    )


def main() -> int:
    print(f"database: {settings.DATABASE_URL.split('@')[-1]}")
    create_tables()
    db = SessionLocal()
    try:
        seed_permissions_and_roles(db)
        seed_admin(db)
        verify_seed(db)
    finally:
        db.close()
    print("database rebuild done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
