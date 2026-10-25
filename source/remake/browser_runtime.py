"""Fixed browser-worker transport for the existing transactional campaign.

The worker mounts trusted source/data files before creating this bridge. Request
payloads can select a known scenario, never a filesystem path or Python code.
Each browser worker owns one session; no shared HTTP game service is involved.
"""
from .view_transport import ViewTransport
from collections import OrderedDict
from copy import deepcopy
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from .campaign import Catalog, GameError
from .json_boundary import DepthLimitError, loads
from .march_core import config_for, using_backend
from .session import CampaignSession, DEFAULT_SCENARIO


MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_CATALOGS = 2
IDENTIFIER = re.compile(r'[a-z0-9][a-z0-9_-]{0,79}')
GET_PATHS = frozenset(('/api/state', '/api/city-preview', '/api/march-config',
                       '/api/march-status', '/api/save'))
POST_PATHS = frozenset(('/api/command', '/api/load'))
COMMANDS = frozenset(('new', 'persuade_officer', 'recruit_officer', 'transfer',
                     'tactic', 'duel_start', 'duel_action', 'allocate', 'recruit',
                     'depart', 'attack', 'retreat', 'settle', 'end_turn', 'ai',
                     'arrivals', 'hire_staff', 'reject_staff', 'staff_recruit',
                     'choose_successor', 'set_domestic', 'set_logistics',
                     'dispatch_transport', 'search_treasure', 'reward_officer',
                     'sell_treasure', 'set_governor', 'set_treasury_policy',
                     'develop_town','treat_officer','study_officer','trade_grain',
                     'buy_equipment','improve_prevention','set_facility_policy','equip_owned'))


def _encode(value):
    # Match the local transport exactly, including spaces and Unicode handling.
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _strict_json(body):
    if not isinstance(body, (str, bytes)):
        raise GameError('操作数据格式无效。')
    raw = body.encode('utf-8') if isinstance(body, str) else body
    if not raw or len(raw) > MAX_BODY_BYTES:
        raise GameError('存档或操作数据大小无效。', 413 if raw else 400)
    try:
        return loads(raw)
    except DepthLimitError:
        raise GameError('操作数据层级过多。') from None


class BrowserRuntime:
    """One isolated, lazy two-catalog session behind a fixed JSON API."""
    def __init__(self, catalog_paths: dict, opening_previews: list,
                 initial_scenario: str = DEFAULT_SCENARIO):
        if (not isinstance(catalog_paths, dict) or not catalog_paths
                or len(catalog_paths) > 256
                or any(not isinstance(key, str) or not IDENTIFIER.fullmatch(key)
                       for key in catalog_paths)):
            raise ValueError('Known catalog paths are required')
        paths = {}
        for key, path in catalog_paths.items():
            if (not isinstance(path, (str, Path)) or not str(path)
                    or len(str(path)) > 4096 or '\x00' in str(path)
                    or not Path(path).is_absolute()):
                raise ValueError('Catalog paths must be absolute trusted paths')
            paths[key] = Path(path)
        if len(set(paths.values())) != len(paths):
            raise ValueError('Each scenario requires a distinct catalog path')
        if (not isinstance(opening_previews, list)
                or any(not isinstance(row, dict) or not isinstance(row.get('id'), str)
                       for row in opening_previews)):
            raise ValueError('Complete opening previews are required')
        preview_ids = [row['id'] for row in opening_previews]
        if (len(preview_ids) != len(set(preview_ids))
                or set(preview_ids) != set(paths)):
            raise ValueError('Opening previews must match the known scenarios')
        if not isinstance(initial_scenario, str) or initial_scenario not in paths:
            raise ValueError('Unknown initial scenario')
        # JSON-only configuration cannot retain caller-owned mutable containers.
        previews = deepcopy(opening_previews)
        _encode(previews)
        self._view_transport = ViewTransport()
        self.catalog_paths = paths
        with using_backend('python'):
            self.session = CampaignSession([paths[initial_scenario]],
                                           initial_scenario=initial_scenario)
        if self.session.game.catalog.data['id'] != initial_scenario:
            raise ValueError('Initial catalog identity does not match its index')
        self.session.catalogs = OrderedDict(self.session.catalogs)
        self.session._opening_previews = previews

    def _catalog(self, scenario):
        if not isinstance(scenario, str) or scenario not in self.catalog_paths:
            raise GameError('请选择有效的战役。')
        cache = self.session.catalogs
        if scenario not in cache:
            try:
                catalog = Catalog(self.catalog_paths[scenario])
                if catalog.data['id'] != scenario:
                    raise ValueError('Catalog identity mismatch')
            except (OSError, ValueError, KeyError, TypeError, AssertionError):
                raise GameError('剧本资料尚未准备好，请重试。', 503) from None
            cache[scenario] = catalog
        cache.move_to_end(scenario)
        active = self.session.game.catalog.data['id']
        while len(cache) > MAX_CATALOGS:
            oldest = next(key for key in cache if key not in (active, scenario))
            del cache[oldest]
        return cache[scenario]

    @staticmethod
    def _query(url, fields):
        if re.search(r'%(?![0-9a-fA-F]{2})', url.query):
            raise GameError('查询参数无效。')
        try:
            query = parse_qs(url.query, keep_blank_values=True,
                             strict_parsing=True, max_num_fields=len(fields),
                             encoding='utf-8', errors='strict')
        except (ValueError, UnicodeError):
            raise GameError('查询参数无效。') from None
        if (set(query) != set(fields)
                or any(len(values) != 1 or not IDENTIFIER.fullmatch(values[0])
                       for values in query.values())):
            raise GameError('查询参数无效。')
        return {key: values[0] for key, values in query.items()}

    def _dispatch(self, path, method, body):
        if (not isinstance(path, str) or not path.startswith('/api/')
                or len(path) > 2048 or re.search(r'[\x00-\x20\x7f\\]', path)):
            raise GameError('未找到这个操作。', 404)
        url = urlsplit(path)
        if url.scheme or url.netloc or '#' in path or url.path not in GET_PATHS | POST_PATHS:
            raise GameError('未找到这个操作。', 404)
        if (url.path in GET_PATHS and method != 'GET'
                or url.path in POST_PATHS and method != 'POST'):
            raise GameError('操作方法无效。', 405)
        if method == 'GET':
            if body not in (None, ''):
                raise GameError('查询不能附带操作数据。')
            if url.path == '/api/city-preview':
                args = self._query(url, ('scenario', 'city'))
                self._catalog(args['scenario'])
                return self.session.preview_city(args['scenario'], args['city'])
            if url.path == '/api/march-config':
                args = self._query(url, ('scenario',))
                return config_for(self._catalog(args['scenario']).data)
            if url.query or '?' in path:
                raise GameError('查询参数无效。')
            if url.path == '/api/state':
                return self.session.view()
            if url.path == '/api/save':
                return self.session.export_save()
            return dict(engine='python', abi=None, calls=0,
                        contexts=0, runtime='browser-worker')
        if url.query or '?' in path:
            raise GameError('操作参数无效。')
        payload = _strict_json(body)
        if not isinstance(payload, dict):
            raise GameError('操作参数无效。')
        if url.path == '/api/command':
            if (set(payload) != {'kind', 'payload', 'revision'}
                    or not isinstance(payload['kind'], str)
                    or payload['kind'] not in COMMANDS
                    or not isinstance(payload['payload'], dict)
                    or type(payload['revision']) is not int):
                raise GameError('操作参数无效。')
            kind, values, revision = payload['kind'], payload['payload'], payload['revision']
            if kind == 'new':
                # A stale switch cannot evict a catalog or construct a new game.
                if revision != self.session.revision:
                    raise GameError('进度已更新，请重新选择操作。', 409)
                self._catalog(values.get('scenario', self.session.game.catalog.data['id']))
            # Keep domain idempotency for already-settled battles / AI turns.
            return self.session.command(kind, values, revision)
        if (set(payload) != {'save', 'revision'}
                or not isinstance(payload['save'], dict)
                or type(payload['revision']) is not int):
            raise GameError('存档或操作参数无效。')
        if payload['revision'] != self.session.revision:
            raise GameError('进度已更新，请重新读取。', 409)
        self._catalog(payload['save'].get('scenario'))
        return self.session.load_save(payload['save'], payload['revision'])

    def dispatch_compact_json(self, path, method='GET', body=None, known=''):
        """Opt-in wire optimization; old callers still receive complete views."""
        if not isinstance(known, str) or (known and not re.fullmatch(r'[a-f0-9]{64}(?::[a-f0-9]{64})?', known)):
            return {'status': 400, 'body': _encode({'error': '视图缓存标识无效。'})}
        return self.dispatch_json(path, method, body, _known=known)

    def dispatch_json(self, path, method='GET', body=None, *, _known=None):
        """Return only status and JSON text; caller input is never executable."""
        try:
            with self.session.lock, using_backend('python'):
                result = self._dispatch(path, method, body)
                if _known is not None:
                    result = self._view_transport.pack(result, self.session.game.catalog.sha256, _known)
                return {'status': 200, 'body': _encode(result)}
        except GameError as exc:
            return {'status': exc.status, 'body': _encode({'error': str(exc)})}
        except (ValueError, TypeError, KeyError, RecursionError, UnicodeError):
            return {'status': 400, 'body': _encode({
                'error': '输入或存档不符合当前规则，进度未改变。'})}
        except Exception:
            # No filesystem locations, Python exception details or source text
            # cross the browser API boundary.
            return {'status': 500, 'body': _encode({
                'error': '操作未完成，请核对当前进度后重试。'})}
