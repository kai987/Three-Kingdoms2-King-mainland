"""Public browser configuration only; cloud sessions never enter the game server."""
from __future__ import annotations

import json
from pathlib import Path
import re


def public_config(path: Path) -> dict:
    """Fail closed if absent/invalid, and never serve a private Supabase key."""
    disabled = dict(enabled=False, slots=5)
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        if value.get('enabled') is not True:
            return disabled
        url, key = value.get('url', ''), value.get('publishableKey', '')
        if not isinstance(url, str) or not re.fullmatch(r'https://[a-z0-9]{20}\.supabase\.co', url):
            return disabled
        if not isinstance(key, str) or not re.fullmatch(r'sb_publishable_[A-Za-z0-9_-]{16,200}', key):
            return disabled
        return dict(enabled=True, url=url, publishableKey=key, slots=5)
    except (OSError, ValueError, AttributeError):
        return disabled


def content_security_policy(config: dict) -> str:
    origin = ' ' + config['url'] if config.get('enabled') else ''
    return ("default-src 'self'; img-src 'self' data:; "
            "script-src 'self' 'wasm-unsafe-eval'; worker-src 'self'; "
            "style-src 'self'; connect-src 'self'" + origin + "; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
