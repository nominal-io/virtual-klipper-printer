"""Nominal client factory.

Creates a NominalClient from environment variables or stored credentials.

Environment variables:
    NOMINAL_API_KEY       — API key for authentication
    NOMINAL_BASE_URL      — Base URL (default: https://api.gov.nominal.io/api)
    NOMINAL_WORKSPACE_RID — Workspace RID to scope requests to
"""

from __future__ import annotations

import os

from nominal.core import NominalClient

DEFAULT_BASE_URL = "https://api.gov.nominal.io/api"


def create_client(
    api_key: str | None = None,
    base_url: str | None = None,
    workspace_rid: str | None = None,
    profile: str = "default",
) -> NominalClient:
    """Create a NominalClient from explicit args, env vars, or stored credentials.

    Resolution order for each parameter:
        1. Explicit argument
        2. Environment variable
        3. Stored profile (fallback when no API key is available)

    Args:
        api_key: Nominal API key. Falls back to ``NOMINAL_API_KEY`` env var.
        base_url: Nominal API base URL. Falls back to ``NOMINAL_BASE_URL`` env var.
        workspace_rid: Workspace RID. Falls back to ``NOMINAL_WORKSPACE_RID`` env var.
        profile: Stored credential profile name. Only used when no API key is available.

    Returns:
        A configured NominalClient.
    """
    api_key = api_key or os.environ.get("NOMINAL_API_KEY")
    base_url = base_url or os.environ.get("NOMINAL_BASE_URL", DEFAULT_BASE_URL)
    workspace_rid = workspace_rid or os.environ.get("NOMINAL_WORKSPACE_RID")

    if api_key:
        return NominalClient.from_token(
            api_key,
            base_url=base_url,
            workspace_rid=workspace_rid,
        )

    return NominalClient.from_profile(profile)
