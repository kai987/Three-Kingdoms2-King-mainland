"""Shared parsing preserves HTTP/worker validation and offline packaging."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from remake.browser_runtime import _strict_json, MAX_BODY_BYTES
from remake.errors import GameError
from remake.json_boundary import DepthLimitError, MAX_JSON_DEPTH, loads


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HTTP = load_module('json_boundary_http', ROOT / 'game/serve.py')


class SharedJSONBoundaryTests(unittest.TestCase):
    def test_values_unicode_and_escaped_delimiters_match_on_both_transports(self):
        values = [None, True, 0, -0.0, 1.25, '漢字、かな',
                  {'text': '[{\\"quoted\\"}]' * 100, 'rows': [False, {'n': 1e100}]}]
        for value in values:
            raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
            for parser in (loads, HTTP.strict_json, _strict_json):
                with self.subTest(value=value, parser=parser.__name__):
                    actual = parser(raw)
                    self.assertEqual(actual, value)
                    self.assertEqual(json.dumps(actual), json.dumps(value))
        self.assertEqual(loads(bytearray(b'{"n":1}')), {'n': 1})
        self.assertEqual(HTTP.strict_json(bytearray(b'{"n":1}')), {'n': 1})

    def test_nested_and_unicode_equivalent_duplicate_keys_are_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"n":{"x":1,"x":2}}',
                    b'{"a":1,"\\u0061":2}'):
            for parser in (loads, HTTP.strict_json, _strict_json):
                with self.subTest(raw=raw, parser=parser.__name__):
                    with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
                        parser(raw)

    def test_non_finite_numbers_bad_utf8_and_malformed_json_still_reject(self):
        invalid = [b'{"n":NaN}', b'{"n":Infinity}', b'{"n":-Infinity}',
                   b'{"n":1e9999}', b'{"n":-1e9999}', b'\xff',
                   b'{', b'{"x":1,}', b'[]{}', b']', b'"unterminated']
        for raw in invalid:
            for parser in (loads, HTTP.strict_json, _strict_json):
                with self.subTest(raw=raw, parser=parser.__name__):
                    with self.assertRaises(ValueError):
                        parser(raw)

    def test_depth_boundary_keeps_each_transport_error_contract(self):
        valid = b'[' * MAX_JSON_DEPTH + b'0' + b']' * MAX_JSON_DEPTH
        for parser in (loads, HTTP.strict_json, _strict_json):
            self.assertEqual(parser(valid), json.loads(valid))
        invalid = b'[' + valid + b']'
        with self.assertRaisesRegex(DepthLimitError, 'JSON nesting limit'):
            loads(invalid)
        with self.assertRaisesRegex(ValueError, 'JSON nesting limit') as rejected:
            HTTP.strict_json(invalid)
        self.assertIs(type(rejected.exception), ValueError)
        with self.assertRaisesRegex(GameError, '操作数据层级过多。') as rejected:
            _strict_json(invalid)
        self.assertEqual(rejected.exception.status, 400)

    def test_worker_type_size_status_and_utf8_limits_stay_transport_owned(self):
        for body in (None, {}, [], bytearray(b'{}')):
            with self.subTest(body_type=type(body).__name__):
                with self.assertRaisesRegex(GameError, '操作数据格式无效。'):
                    _strict_json(body)
        with self.assertRaises(GameError) as rejected:
            _strict_json('')
        self.assertEqual(rejected.exception.status, 400)
        body = b'{}' + b' ' * (MAX_BODY_BYTES - 2)
        self.assertEqual(_strict_json(body), {})
        for body in (body + b' ', '漢' * (MAX_BODY_BYTES // 3 + 1)):
            with self.assertRaises(GameError) as rejected:
                _strict_json(body)
            self.assertEqual(rejected.exception.status, 413)

    def test_shared_module_runs_from_offline_bundle_without_project_path(self):
        builder = load_module('json_boundary_web_builder', ROOT / 'game/build_web.py')
        with tempfile.TemporaryDirectory(prefix='tk2-json-bundle-') as directory:
            output = Path(directory)
            manifest = builder.python_bundle(output)
            archive = output / manifest['url']
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(bundle.read('source/remake/json_boundary.py'),
                                 (ROOT / 'source/remake/json_boundary.py').read_bytes())
            code = ("import sys;sys.path.insert(0,sys.argv[1]+'/source');"
                    "from remake.json_boundary import loads;"
                    "assert loads(b'{\"n\":1}')=={'n':1}")
            subprocess.run([sys.executable, '-I', '-S', '-B', '-c', code, str(archive)],
                           cwd=output, check=True, capture_output=True, timeout=10)


if __name__ == '__main__':
    unittest.main()
