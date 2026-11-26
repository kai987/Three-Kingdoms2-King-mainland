#!/usr/bin/env python3
"""Build an offline, source-attributed Traditional Chinese display dictionary.

Published game catalogs and save data remain in their original representation.
Only presentation text is converted, using OpenCC dictionaries pinned below.
"""
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'game'
SOURCE = HERE / 'locales/opencc'


def dictionary(name):
    rows = {}
    for line in (SOURCE / name).read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        before, after = line.split('\t', 1)
        rows[before] = after.split(' ')[0]
    return rows


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def corpus():
    texts = set()
    paths = [HERE / 'index.html', HERE / 'app.js']
    paths += sorted((ROOT / 'source/remake').glob('*.py'))
    paths += sorted((HERE / 'config').glob('*.json'))
    latest = HERE / 'data/campaigns'
    paths += sorted(latest.glob('*.json'))
    # Locale keys can contain UI text added outside app.js.
    paths += sorted((HERE / 'locales').glob('*-ja.json'))
    for path in paths:
        if path.suffix == '.json':
            texts.update(strings(json.loads(path.read_text())))
        else:
            texts.add(path.read_text())
    return texts


def used_phrases(phrases, texts):
    trie = {}
    for key in phrases:
        node = trie
        for char in key:
            node = node.setdefault(char, {})
        node[''] = key
    used = set()
    for text in texts:
        for start in range(len(text)):
            node = trie
            for char in text[start:]:
                node = node.get(char)
                if node is None:
                    break
                if '' in node:
                    used.add(node[''])
    return {key: phrases[key] for key in sorted(used)}


def convert(text, stage):
    phrases, characters = stage['phrases'], stage['characters']
    groups = {}
    for key in phrases:
        groups.setdefault(key[0], []).append(key)
    for group in groups.values():
        group.sort(key=lambda key: (-len(key), key))
    result, cursor = [], 0
    while cursor < len(text):
        word = next((word for word in groups.get(text[cursor], []) if text.startswith(word, cursor)), None)
        result.append(phrases[word] if word else characters.get(text[cursor], text[cursor]))
        cursor += len(word) if word else 1
    return ''.join(result)


def build(output=HERE / 'locales/zh-hant.json'):
    metadata = json.loads((SOURCE / 'source.json').read_text())
    for name, info in metadata['files'].items():
        if hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('Pinned OpenCC source changed: ' + name)
    phrases = dictionary('STPhrases.txt')
    first = dict(phrases=used_phrases(phrases, corpus()), characters=dictionary('STCharacters.txt'))
    second = dict(phrases={}, characters=dictionary('TWVariants.txt'))
    # Historical proper names must retain surname 于/范/干/余/游. These are
    # semantic exceptions to modern prose conversion, not new officer data.
    people = json.loads((HERE / 'data/campaigns/217-07.json').read_text())['people']
    for person in people:
        name = person['name']
        if name.startswith(('于', '范', '干', '余', '游')):
            first['phrases'][name] = name[0] + convert(name[1:], first)
    first['phrases'].update({'刘辟': '劉辟', '钟会': '鍾會', '钟繇': '鍾繇',
                              '于吉': '于吉', '范疆': '范疆', '范强': '范強'})
    first['phrases']['于夫罗'] = '於夫羅'
    for stage in (first, second):
        for field in ('phrases', 'characters'):
            stage[field] = dict(sorted(stage[field].items()))
    value = dict(schema='opencc-subset-v1', locale='zh-Hant',
        attribution='OpenCC ver.1.1.9, Apache-2.0; corpus-filtered phrases and historical name exceptions added by this project.',
        source_revision=metadata['revision'], stages=[first, second])
    # Test builders can target private paths. Real readers see an entire
    # previous or next dictionary even when two generators finish together.
    output = Path(output)
    temporary = None
    try:
        with NamedTemporaryFile(dir=output.parent, mode='w', encoding='utf-8', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')
        temporary.chmod(0o644)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return value


if __name__ == '__main__':
    result = build()
    print(json.dumps(dict(locale=result['locale'], phrases=len(result['stages'][0]['phrases']),
                          characters=len(result['stages'][0]['characters']))))
