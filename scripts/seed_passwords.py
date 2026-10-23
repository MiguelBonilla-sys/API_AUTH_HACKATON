"""Passwords for seeded accounts: random per account, never hard-coded or shared.

Set SEED_ADMIN_PASSWORD to choose the admin password; every other account gets
its own random password, written only to the git-ignored credentials files.
"""
import os
import secrets


def seed_password(env_var: str | None = None) -> str:
    if env_var and os.getenv(env_var):
        return os.environ[env_var]
    return secrets.token_urlsafe(16)
