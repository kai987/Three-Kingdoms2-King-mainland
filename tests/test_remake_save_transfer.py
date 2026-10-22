"""Current pending marches retain their exact checksum through browser IO."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign,Catalog,canonical,digest,GameError


class SaveTransferTests(unittest.TestCase):
    def test_current_fractional_risk_save_browser_roundtrip_and_tamper_rejection(self):
        catalog=Catalog(ROOT/'game/data/campaigns/217-07.json')
        game=Campaign(catalog)
        game.command('new',dict(faction='wei',seed=2026),0)
        ident=game.state.cities['yinping'].roster.officer_ids[0]
        game.command('depart',dict(source='yinping',target='shujun',officers=[ident],route_mode='special'),game.revision)
        saved=game.export_save()
        leg=saved['state']['extension']['travel']['marches'][0]['quote']['routes'][0]
        self.assertEqual(leg['hazard']['loss_percent'],200/3)
        self.assertIs(type(leg['hazard']['loss_percent']),float)
        raw=json.dumps(saved,ensure_ascii=False,allow_nan=False)
        script="const fs=require('fs'),{loadBody}=require('./game/save-transfer.js');process.stdout.write(loadBody(fs.readFileSync(0,'utf8'),0));"
        body=subprocess.check_output(['node','-e',script],input=raw,text=True,cwd=ROOT)
        payload=json.loads(body)
        self.assertEqual(canonical(payload['save']),canonical(saved))
        restored=Campaign(catalog)
        restored.load_save(payload['save'],payload['revision'])
        self.assertEqual(canonical(restored.export_save()),canonical(saved))
        before=canonical(restored.export_save())
        bad=json.loads(raw)
        bad['state']['extension']['travel']['marches'][0]['quote']['routes'][0]['hazard']['loss_percent']=66
        self.assertNotEqual(digest({k:v for k,v in bad.items() if k!='checksum'}),saved['checksum'])
        with self.assertRaises(GameError):restored.load_save(bad,restored.revision)
        self.assertEqual(canonical(restored.export_save()),before)


if __name__=='__main__':unittest.main()
