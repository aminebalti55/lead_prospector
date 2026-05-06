"""Single shared Supabase client for the backend.

Always uses the SERVICE-ROLE key. RLS is enabled on every table; this
client is the only path that bypasses RLS, and it MUST stay server-side.
The publishable/anon key is for the React frontend only.

Connection-test policy:
- Module load is silent (no network calls).
- Call `verify_connection()` from a startup hook to fail fast if env is wrong.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def _required(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise RuntimeError(
            f"{name} is not set. Add it to .env. Without it the backend "
            f"cannot read or write to Supabase."
        )
    return v


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Return the shared service-role Supabase client.

    Cached for the process lifetime. Calling this from request handlers is
    cheap — the underlying httpx client pools connections."""
    url = _required("SUPABASE_URL")
    key = _required("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def verify_connection() -> dict:
    """Probe Supabase to confirm credentials work. Returns a dict suitable
    for /api/health. Never raises — failures land in the response body."""
    try:
        client = get_client()
        # Cheapest possible probe: count templates (we just seeded 10).
        resp = client.table("templates").select("id", count="exact").limit(1).execute()
        return {
            "supabase": "ok",
            "templates_count": resp.count if resp.count is not None else 0,
        }
    except Exception as e:
        return {"supabase": "error", "error": str(e)}
