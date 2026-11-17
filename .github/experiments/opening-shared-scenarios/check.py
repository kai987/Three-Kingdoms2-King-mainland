"""Check that the experimental cache refills safely without changing old callers."""
from pathlib import Path
from runpy import run_path

from remake.view_transport import ViewTransport

value = {'game':None, 'revision':0, 'catalog':{'title':'sample','library':[],
         'scenarios':[{'id':'a'}], 'travel_quotes':{}}}
source='0'*64
expected=ViewTransport().pack(value, source)
script=run_path(str(Path(__file__).with_name('worker-profile.py')))
namespace=script['_pack_with_shared_scenarios'].__globals__
namespace['_experimental_preview_sha']='a'*64
transport=ViewTransport()
row=lambda: dict(pack_ms=0,static_json_ms=0,static_sha_ms=0,shared_json_ms=0,shared_sha_ms=0)
preview=object()

def pack(value, known, previews=preview):
    namespace['_active']=(row(),known,previews)
    return transport.pack(value, source)

first=pack(value,'')
token=first['scenarios_token']
assert first['shared_scenarios']==value['catalog']['scenarios']
assert 'scenarios' not in first['static_catalog']
warm=pack(value,token)
assert warm['scenarios_token']==token and 'shared_scenarios' not in warm
assert pack(value,'0'*64)['shared_scenarios']==first['shared_scenarios']
assert pack(value,None)==expected

replacement=dict(value,catalog=dict(value['catalog'],scenarios=[{'id':'b'}]))
namespace['_experimental_preview_sha']='b'*64
changed=pack(replacement,token,object())
assert changed['scenarios_token']!=token
assert changed['shared_scenarios']==replacement['catalog']['scenarios']
print('Cache miss, warm reuse, stale token, version change and original-client fallback passed.')
