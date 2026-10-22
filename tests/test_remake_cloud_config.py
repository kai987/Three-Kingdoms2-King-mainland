"""Cloud config must expose only a validated public endpoint and key."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.cloud_config import content_security_policy, public_config


class CloudConfigTests(unittest.TestCase):
    def read(self, value):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cloud.json'
            path.write_text(json.dumps(value))
            return public_config(path)

    def test_public_config_and_exact_connect_origin(self):
        config = self.read(dict(enabled=True, url='https://' + 'a' * 20 + '.supabase.co',
                                publishableKey='sb_publishable_' + 'b' * 25, secret='not served'))
        self.assertEqual(set(config), {'enabled', 'url', 'publishableKey', 'slots'})
        self.assertEqual(config['slots'], 5)
        policy = content_security_policy(config)
        self.assertIn("connect-src 'self' https://" + 'a' * 20 + '.supabase.co;', policy)
        self.assertNotIn('*', policy)
        self.assertNotIn('unsafe-inline', policy)

    def test_private_keys_untrusted_origins_and_bad_documents_disable_cloud(self):
        valid = dict(enabled=True, url='https://' + 'a' * 20 + '.supabase.co',
                     publishableKey='sb_publishable_' + 'b' * 25)
        for key in ('sb_secret_no', 'service_role', 'eyJhbGciOiJIUzI1NiJ9'):
            self.assertFalse(self.read(dict(valid, publishableKey=key))['enabled'])
        for url in ('http://example.com', 'https://evil.example', valid['url'] + '/x',
                    valid['url'] + "; script-src *", 'https://user@' + 'a' * 20 + '.supabase.co'):
            self.assertFalse(self.read(dict(valid, url=url))['enabled'])
        for value in (None, [], {}, dict(valid, enabled=False)):
            self.assertFalse(self.read(value)['enabled'])
        self.assertEqual(content_security_policy(dict(enabled=False)).split('connect-src ')[1].split(';')[0], "'self'")


if __name__ == '__main__':
    unittest.main()
