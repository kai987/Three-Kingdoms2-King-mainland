#!/usr/bin/env python3
"""Rebuild exact ROM bytes from ordered .byte source and verify each digest."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]

def rebuild(output):
    src=ROOT/'source/byte-source'
    order=json.loads((src/'order.json').read_text())
    result=bytearray()
    for chunk in order['chunks']:
        data=bytearray()
        for line in (src/chunk['file']).read_text().splitlines():
            code=line.split(';',1)[0].strip()
            if not code:
                continue
            if not re.fullmatch(r'\.byte \$[0-9A-F]{2}(, \$[0-9A-F]{2})*',code):
                raise ValueError(f"Invalid byte directive in {chunk['file']}: {line}")
            data.extend(int(x,16) for x in re.findall(r'\$([0-9A-F]{2})',code))
        assert len(result)==chunk['offset'], f"Noncontiguous {chunk['file']}"
        assert len(data)==chunk['length'], f"Length mismatch {chunk['file']}"
        assert hashlib.sha256(data).hexdigest()==chunk['sha256'], f"Digest mismatch {chunk['file']}"
        result.extend(data)
    sha=hashlib.sha256(result).hexdigest()
    assert len(result)==order['rom_length'] and sha==order['rom_sha256']
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(result)
    print(json.dumps({'output':str(output.resolve()),'bytes':len(result),'sha256':sha,'verified':True}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'build/三国志2超级版.rebuilt.nes')
    rebuild(p.parse_args().output)
