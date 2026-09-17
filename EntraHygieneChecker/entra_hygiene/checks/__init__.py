"""Hygiene check analyzers (pure functions over Graph-shaped data)."""

from entra_hygiene.checks.apps import analyze_app_hygiene, collect_app_hygiene
from entra_hygiene.checks.guests import analyze_guests, collect_guests
from entra_hygiene.checks.mfa import analyze_mfa, collect_mfa
from entra_hygiene.checks.roles import analyze_privileged_roles, collect_privileged_roles

__all__ = [
    "analyze_mfa",
    "collect_mfa",
    "analyze_guests",
    "collect_guests",
    "analyze_app_hygiene",
    "collect_app_hygiene",
    "analyze_privileged_roles",
    "collect_privileged_roles",
]
