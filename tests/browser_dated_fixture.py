"""Serve controlled dated scenarios through the actual local HTTP game server.

Only the initial catalog is controlled. New games, ten-day turns, historical
events, succession, saves and the rendered frontend use production services.
No campaign state, save, RNG or transaction result is injected by this wrapper.

Examples:
    python3 -B tests/browser_dated_fixture.py --kind founding --port 18921
    python3 -B tests/browser_dated_fixture.py --kind retirement --port 18922
    python3 -B tests/browser_dated_fixture.py --kind coup --port 18923
"""
import argparse
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'source'), str(ROOT / 'tests'), str(ROOT / 'game')]

from campaign_dated_fixtures import dated_catalog
from remake.session import CampaignSession as RealSession
import remake.session as sessions


def main():
    # Consume only this wrapper's selector. Production serve.py continues to
    # own --port, --audit-log and its normal argument validation.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--kind', choices=('founding', 'retirement', 'coup'), default='founding')
    options, remaining = parser.parse_known_args()
    sys.argv = [sys.argv[0], *remaining]
    catalog = dated_catalog(options.kind)

    def fixture_session(paths):
        with patch.object(sessions, 'Catalog', return_value=catalog):
            return RealSession([ROOT / ('controlled-dated-' + options.kind + '.json')])

    sessions.CampaignSession = fixture_session
    import serve
    serve.main()


if __name__ == '__main__':
    main()
