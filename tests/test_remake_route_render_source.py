"""Accept UI-only edits without weakening frozen route geometry inputs."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game'))
from route_render_source import (APP_SOURCE, ATTESTATION_PATH, COMPILER_SOURCE,
                                 END, START, renderer_projection,
                                 validate_app_projection,
                                 validate_geometry_sources)


class RouteRenderSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((ROOT / 'game/config/route-geometry.json').read_text())['sources']
        cls.attestation = json.loads((ROOT / ATTESTATION_PATH).read_text())
        cls.app = (ROOT / APP_SOURCE).read_bytes()
        cls.original_pin = cls.sources[APP_SOURCE]
        cls.compiler_pin = cls.sources[COMPILER_SOURCE]

    def validate(self, source=None, attestation=None):
        validate_app_projection(self.app if source is None else source,
                                self.original_pin, self.compiler_pin,
                                self.attestation if attestation is None else attestation)

    def test_current_projection_matches_exact_frozen_compiler_selection(self):
        compiler = (ROOT / COMPILER_SOURCE).read_bytes()
        self.assertEqual(sha256(compiler).hexdigest(), self.compiler_pin)
        self.assertIn(b"app.slice(app.indexOf('function smoothMapPath('),app.indexOf('function mapBackgroundHref('))", compiler)
        text = self.app.decode('utf-8')
        expected = text[text.index(START):text.index(END)].encode('utf-8')
        self.assertEqual(renderer_projection(self.app), expected)
        self.assertEqual(sha256(expected).hexdigest(), self.attestation['projection_sha256'])
        self.assertEqual(len(expected), self.attestation['projection_bytes'])
        self.validate()
        validate_geometry_sources(ROOT, self.sources)

    def test_unrelated_prefix_suffix_and_background_url_changes_are_accepted(self):
        changed = b'// A new display-only handler.\n' + self.app + b'\n// Another menu.\n'
        self.assertNotEqual(sha256(changed).hexdigest(), self.original_pin)
        self.assertEqual(renderer_projection(changed), renderer_projection(self.app))
        self.validate(changed)
        # mapBackgroundHref is beyond the compiler's final bound. Changing its
        # image URL policy must not invalidate the frozen movement/save data.
        changed = self.app.replace(b'function mapBackgroundHref(original){',
                                   b'function mapBackgroundHref(original){\n // Asset base changed.\n')
        self.validate(changed)

    def test_path_function_whitespace_or_behavior_changes_are_rejected(self):
        for old, new in [(b'return d+`L', b'return d +`L'),
                         (b'Math.hypot(c[0]-p[0],c[1]-p[1])<=3', b'Math.hypot(c[0]-p[0],c[1]-p[1])<=4')]:
            self.assertIn(old, self.app)
            with self.assertRaisesRegex(ValueError, 'source differs'):
                self.validate(self.app.replace(old, new))

    def test_missing_duplicate_and_reversed_projection_bounds_fail_closed(self):
        for source in [self.app.replace(START.encode(), b'function renamed('),
                       START.encode() + self.app, self.app + END.encode(),
                       END.encode() + b'\n' + START.encode()]:
            with self.assertRaises(ValueError):
                self.validate(source)

    def test_stale_baseline_compiler_scope_and_attestation_shapes_fail_closed(self):
        mutations = [dict(original_source_sha256='0' * 64),
                     dict(compiler_sha256='0' * 64),
                     dict(source='game/cloud-save.js'), dict(compiler='other.js'),
                     dict(start='function landMapPath('), dict(end='function unrelated('),
                     dict(projection_sha256='0' * 64), dict(projection_bytes=True),
                     dict(projection_bytes=self.attestation['projection_bytes'] - 1),
                     dict(schema='unreviewed'), dict(baseline_commit='invalid'),
                     dict(extra='not ignored')]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                changed = dict(self.attestation, **mutation)
                with self.assertRaises(ValueError):
                    self.validate(attestation=changed)
        changed = deepcopy(self.attestation)
        del changed['original_source_sha256']
        with self.assertRaises(ValueError):
            self.validate(attestation=changed)

    def test_other_sources_remain_full_file_pinned_and_exact_app_needs_no_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / APP_SOURCE
            app.parent.mkdir(parents=True)
            app.write_bytes(self.app)
            compiler = root / COMPILER_SOURCE
            compiler.write_bytes((ROOT / COMPILER_SOURCE).read_bytes())
            sources = {APP_SOURCE: sha256(self.app).hexdigest(), COMPILER_SOURCE: self.compiler_pin}
            # No attestation is read when the entire app is still exactly pinned.
            validate_geometry_sources(root, sources)
            sources[APP_SOURCE] = self.original_pin
            (root / ATTESTATION_PATH).parent.mkdir(parents=True)
            (root / ATTESTATION_PATH).write_text(json.dumps(self.attestation))
            validate_geometry_sources(root, sources)
            compiler.write_bytes(compiler.read_bytes() + b'\n// Changed compiler.\n')
            with self.assertRaisesRegex(ValueError, COMPILER_SOURCE):
                validate_geometry_sources(root, sources)


if __name__ == '__main__':
    unittest.main()
