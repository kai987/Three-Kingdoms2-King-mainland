"""Real legacy pending marches retain their exact checksum through browser IO."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,canonical,digest,GameError


class SaveTransferTests(unittest.TestCase):
    def test_browser_payload_preserves_legacy_float_spelling_and_rejects_changed_checksum(self):
        catalog=Catalog(ROOT/'game/data/main-scenarios-v10/217-07.json')
        game=Campaign(catalog)
        game.command('new',dict(faction='wu',seed=2026),0)
        ident=game.state.cities['changsha'].roster.officer_ids[0]
        game.command('transfer',dict(source='changsha',target='guiyang',officers=[ident],route_mode='land'),game.revision)
        saved=game.export_save()
        leg=saved['state']['extension']['travel']['marches'][0]['quote']['routes'][0]
        self.assertIs(type(leg['distance_km']),float)
        self.assertEqual(leg['distance_km'],315.0)
        raw=json.dumps(saved,ensure_ascii=False,allow_nan=False)
        script="const fs=require('fs'),{loadBody}=require('./game/save-transfer.js');process.stdout.write(loadBody(fs.readFileSync(0,'utf8'),0));"
        body=subprocess.check_output(['node','-e',script],input=raw,text=True,cwd=ROOT)
        payload=json.loads(body)
        self.assertEqual(canonical(payload['save']),canonical(saved))
        restored=Campaign(catalog)
        restored.load_save(payload['save'],payload['revision'])
        self.assertEqual(canonical(restored.export_save()),canonical(saved))
        # The old parse/stringify path is a real checksum change. Keep rejecting
        # it atomically; do not weaken save validation to hide browser damage.
        normalized=json.loads(raw,parse_float=lambda s:int(float(s)) if float(s).is_integer() else float(s))
        content={k:v for k,v in normalized.items() if k!='checksum'}
        self.assertNotEqual(digest(content),saved['checksum'])
        before=canonical(restored.export_save())
        with self.assertRaises(GameError):restored.load_save(normalized,restored.revision)
        self.assertEqual(canonical(restored.export_save()),before)


if __name__=='__main__':unittest.main()
