#!/usr/bin/env python3
"""Check retained native siege captures and derivatives without ROM/emulator.

Only small immutable data tables and native video callback PNGs are read. This
checker certifies exact capture/crop/4x pixels, not the reconstructed battle AI
or numerical combat rules. Difference candidates are explicitly not clean unit
sprites: the original BG unit tiles overwrite the brick pattern with flat background.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'game/assets/siege-original'
PREFIX = '/assets/siege-original/'
ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CORE_SHA = '924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
HEX = re.compile(r'[0-9a-f]{64}\Z')
PUBLIC = re.compile(re.escape(PREFIX) + r'[a-z0-9_-]+\.(?:png|json)\Z')
CAPTURE_HASHES = {
 'capture-prelude1.png':'81098e6cbb9bd985e2239d1362ed80d00524687404b61490a434525d721a0016',
 'capture-wait-1.png':'a4cb751bef90a5284962ce86b3d73e093093652772dadee7ad609f351b0e3d76',
 'capture-wait-4.png':'9b47c40c54e989c9249091d9ce0c0d3a3547062037c801992a90f27f1663a8be',
 'capture-wait-8.png':'b6659cd14ace33edd781ea459a0a1ed02f397b23adfdd64d2e646bae03c00f62',
 'capture-original-field.png':'2e4eaebc9fc513e67e8f845ab3c9ab67e71a02084ba1b7e4af5f71549cd6bbaa',
}
CAPTURE_HASHES.update({'capture-action-move-general-0.png': '73a0b97b844a92ec635a57e0d24751a962bf9d69cb54c44a2d667eba04bc9822', 'capture-action-move-general-1.png': '656fd2aee13ee2f98b3d54e088a40b8a0ffee8ad1f8a267b3309b78bc976cc9c', 'capture-action-move-infantry-0.png': '10deac157a4b381f1b3f8f6bfdec322fcc02e4b3b6f9480b6f350ab1312f2068', 'capture-action-move-infantry-1.png': '622dd230fbf898e804233a2acefa3c9fd48a917b5bfc371b78d9fa0a98df8678', 'capture-action-move-archer-0.png': '6b910644219058b42cb816d945fb841b2296db2f2e5ffbf706e912bb13f279c3', 'capture-action-move-archer-1.png': 'c7ad2eb1fe6a31f7f73dcca2d39359ca0f54307a999ae64f134da3e88e4bd9fd', 'capture-action-move-cavalry-0.png': 'eefb26839bca1441033ff8eeb6ffaf402e871a75cbca46ebd3a167185b95bce0', 'capture-action-move-cavalry-1.png': '31e6bbe55adfa5da3c6d27114311d248289ef2926563a125396d89a7ec37bf09', 'capture-action-effect-melee.png': '3a9349b102053fe39068a316af9dfa7fa57175409d3e655786d6331f850892ae', 'capture-action-effect-arrow.png': 'a83ceac57a2cd74c361934c96bc5ba47369813dff47e9f0e638b68635f01a937'})
ANIMATION_CHR_HASHES = {'native-sprite-general-friendly-move-0': 'e7a3e384d238a8cd5c9a7bed742758cf56c84ff379b1fa1d7c02ce6633316998', 'native-sprite-general-enemy-move-0': 'e7a3e384d238a8cd5c9a7bed742758cf56c84ff379b1fa1d7c02ce6633316998', 'native-sprite-general-friendly-move-1': 'a520b75732837f3d0ebe781fa683d6dc69c5cc50a1ba6da443e053e8cea31065', 'native-sprite-general-enemy-move-1': 'a520b75732837f3d0ebe781fa683d6dc69c5cc50a1ba6da443e053e8cea31065', 'native-sprite-infantry-friendly-move-0': 'bbc9ce7bd75dad4bb6ba7f53df178c96b23d341c016fa5d0d45679ff51fce2e9', 'native-sprite-infantry-enemy-move-0': 'bbc9ce7bd75dad4bb6ba7f53df178c96b23d341c016fa5d0d45679ff51fce2e9', 'native-sprite-infantry-friendly-move-1': '159240a168e55d65c68e999e1b46fc8973260f51e24f865d3eb34901e63934ad', 'native-sprite-infantry-enemy-move-1': '159240a168e55d65c68e999e1b46fc8973260f51e24f865d3eb34901e63934ad', 'native-sprite-archer-friendly-move-0': 'afe7db3ffa1e31d80e4a2dbd04992fc38b97e73e0185aa5edbe7a5520acd9f76', 'native-sprite-archer-enemy-move-0': 'afe7db3ffa1e31d80e4a2dbd04992fc38b97e73e0185aa5edbe7a5520acd9f76', 'native-sprite-archer-friendly-move-1': '4abe8f45764e2eab3bdef5ffb91830d01c17a71dc6a62f22ee71b2a8f2a3ea7a', 'native-sprite-archer-enemy-move-1': '4abe8f45764e2eab3bdef5ffb91830d01c17a71dc6a62f22ee71b2a8f2a3ea7a', 'native-sprite-cavalry-friendly-move-0': 'b99dcfc18e7e691868e7b20b32a747ccbda6cd2ec4bbdf876e38ddf5c193e19d', 'native-sprite-cavalry-enemy-move-0': 'b99dcfc18e7e691868e7b20b32a747ccbda6cd2ec4bbdf876e38ddf5c193e19d', 'native-sprite-cavalry-friendly-move-1': '79fe310aa286cf3905fdf25002bf87ceb29753559553a5b060322228e2a043ea', 'native-sprite-cavalry-enemy-move-1': '79fe310aa286cf3905fdf25002bf87ceb29753559553a5b060322228e2a043ea', 'native-effect-melee': '2733fbcb886ac67025605ddd713d2a93753f2e57dd9a1754631c0f6944deb89c', 'native-effect-arrow': '6c65352607907471e12bd2192b53bafcc9f10114065a506808504d2cec31f776'}
CHR_HASHES = {
 'native-sprite-general-friendly':'a701b957984320c5b3e9999c755f235806cbac4331ad373f46aaf61378b65b15',
 'native-sprite-infantry-friendly':'9020d20e27c08b89e7d2385ccf4ee5ce3475a1e9ccc94d99e85c07f3f3b1c6e9',
 'native-sprite-archer-friendly':'4dd1d4b9f6a7c815eebdd643c9a289b28e8e588af3d25d627df579b071358000',
 'native-sprite-cavalry-friendly':'bf90930c2687904c47008f727e79051ebf6f3003fcc4cb779277d786bbac56dd',
 'native-sprite-general-enemy':'e7a3e384d238a8cd5c9a7bed742758cf56c84ff379b1fa1d7c02ce6633316998',
 'native-sprite-archer-enemy':'afe7db3ffa1e31d80e4a2dbd04992fc38b97e73e0185aa5edbe7a5520acd9f76',
 'native-sprite-cavalry-enemy':'b99dcfc18e7e691868e7b20b32a747ccbda6cd2ec4bbdf876e38ddf5c193e19d',
 'native-sprite-infantry-enemy':'bbc9ce7bd75dad4bb6ba7f53df178c96b23d341c016fa5d0d45679ff51fce2e9',
}
TABLE_HASHES = {
 'formation_x_pointers':'707fc98744d2c523e5a22405c3892ed562f1673ccb605177d30c27078ad0dff9',
 'formation_y_pointers':'392cef3116444723d5d985f7e47105eec38d398654a7371ea9995bfaa48d057c',
 'formation_x':'b1def7cf4f9eaceaa4bf7a4fc269b007b43473784fde8d7d02fff3ecbf769b91',
 'formation_y':'0d82cfe44b6d8fcfbf02b63a414fbe763e32c2285cbe4110c5e08ecac65dbf87',
 'troop_type_thresholds':'a5c970c66d02eefdfabd03d001b27710589e853d7ff8ff482d39f139fc438411',
 'action_type_order':'0714146c8fe6ae04f23d44476c0658ed157c4f65d8920a8c11a009b4daace2c6',
 'background_pointers':'98fa8c4ab3836f80a256c26fc71bb073bd299f02e5fe55a55fb791a27c68492f',
 'background_banks':'e642f1cb19f1acf4b484d0545b5c50e45bc5b93471cd8c80e5b436311c5779a8',
 'terrain_classes':'9c38767186ba2d9985b7b7513a2a3b5a65e714feff84b0ab38c7f230b8428856',
 'castle_layout':'771d02493dfbc9b3a3d95acb799aeec2becdc58b12dcbd40c1ed30089b909b7e',
}
_spec = importlib.util.spec_from_file_location('siege_native_png',ROOT/'game/build_portrait_manifest.py')
_png = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_png)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def public_path(value):
    require(isinstance(value,str) and PUBLIC.fullmatch(value) is not None,'Unsafe siege asset path')
    return value


def safe_read(root, path):
    path = public_path(path)
    current = Path(root)
    require(not current.is_symlink(),'Symlink siege asset directory')
    for part in Path(path.removeprefix(PREFIX)).parts:
        current = current/part
        require(not current.is_symlink(),'Symlink siege asset file')
    return current.read_bytes()


def pixels(raw, size):
    require(len(size)==2 and all(type(n) is int and 0<n<=2048 for n in size),'Invalid PNG size')
    return _png.png_pixels(raw,tuple(size))[1]


def crop(raw, size, rect):
    require(isinstance(rect,list) and len(rect)==4 and all(type(v)is int for v in rect),'Invalid source rectangle')
    left,top,right,bottom = rect
    require(0<=left<right<=size[0] and 0<=top<bottom<=size[1],'Source rectangle out of bounds')
    return b''.join(raw[(y*size[0]+left)*4:(y*size[0]+right)*4] for y in range(top,bottom)),(right-left,bottom-top)


def nearest4(raw, size):
    width,height = size
    return b''.join(b''.join(raw[(y*width+x)*4:(y*width+x+1)*4]*4 for x in range(width))*4 for y in range(height))


def native_sprite(key, operation, opaque):
    """Verify original CHR against video before removing background indices.

    Friendly armor and the brick ground share RGB gray, but use different
    original pattern indices. RGB color-keying would silently erase the armor.
    """
    tiles=operation.get('tiles',[]);palette=operation.get('palette_rgb',[])
    require(key in CHR_HASHES and len(tiles)==4 and len(palette)==4,'Invalid native CHR sprite')
    require(all(len(color)==3 and all(type(v)is int and 0<=v<=255 for v in color)for color in palette),'Invalid native CHR palette')
    background=1 if key.endswith('friendly') else 0
    require(operation.get('transparent_index')==background,'Wrong original background pattern index')
    combined=bytearray();rendered=bytearray(1024);transparent=bytearray(1024);locations=set()
    for tile in tiles:
        raw=bytes.fromhex(tile['hex']);page=tile['chr_page_1k'];ident=tile['tile_id'];dx,dy=tile['dx'],tile['dy']
        require(len(raw)==16 and sha(raw)==tile['sha256'],'Native CHR tile changed')
        require((dx,dy)in ((0,0),(8,0),(0,8),(8,8)) and (dx,dy)not in locations,'Invalid native CHR tile placement')
        require(tile['rom_offset']==0x40010+page*1024+(ident%64)*16,'Native CHR tile offset mismatch')
        locations.add((dx,dy));combined.extend(raw)
        for y in range(8):
            for x in range(8):
                index=(raw[y]>>(7-x)&1)|(raw[y+8]>>(7-x)&1)<<1
                at=((dy+y)*16+dx+x)*4
                rendered[at:at+4]=bytes([*palette[index],255])
                transparent[at:at+4]=bytes([*palette[index],0 if index==background else 255])
    require(sha(combined)==operation.get('chr_composite_sha256')==CHR_HASHES[key],'Unverified native CHR composite')
    require(bytes(rendered)==opaque,'Original CHR does not match the native video crop')
    return bytes(transparent)


def animation_sprite(key,operation,opaque,size):
    """Original OAM priority, CHR masks and verified native palette variants."""
    tiles=operation.get('tiles',[]);palette=operation.get('palette_rgb',[])
    verification=operation.get('verification_palette_rgb',[])
    require(key in ANIMATION_CHR_HASHES and len(tiles)in (1,4)and operation.get('transparent_index')==0,'Invalid original OAM animation')
    allowed=[[[0,0,0],[0,0,0],[255,213,203],[167,181,188]],[[0,0,0],[0,0,0],[255,213,203],[187,45,9]],[[0,0,0],[0,0,0],[255,255,255],[187,45,9]]]
    require(palette in allowed and verification in allowed,'Unverified original animation palette')
    rendered=bytearray(size[0]*size[1]*4);confirmed=bytearray(len(rendered));combined=bytearray()
    for tile in tiles:
        raw=bytes.fromhex(tile['hex']);combined.extend(raw)
        require(len(raw)==16 and sha(raw)==tile['sha256'],'OAM CHR tile changed')
        require(tile['rom_offset']==0x40010+tile['chr_page_1k']*1024+(tile['tile_id']%64)*16,'OAM CHR offset mismatch')
        require(type(tile['flip_x'])is bool and type(tile['flip_y'])is bool,'Invalid native OAM flip')
        dx,dy=tile['dx'],tile['dy']
        require(type(dx)is int and type(dy)is int and 0<=dx<=size[0]-8 and 0<=dy<=size[1]-8,'Invalid native OAM placement')
        for y in range(8):
            for x in range(8):
                tx=7-x if tile['flip_x']else x;ty=7-y if tile['flip_y']else y
                index=(raw[ty]>>(7-tx)&1)|(raw[ty+8]>>(7-tx)&1)<<1
                at=((dy+y)*size[0]+dx+x)*4
                if index and not rendered[at+3]:
                    rendered[at:at+4]=bytes([*palette[index],255])
                    confirmed[at:at+4]=bytes([*verification[index],255])
    require(sha(combined)==operation.get('chr_composite_sha256')==ANIMATION_CHR_HASHES[key],'Unverified native animation CHR')
    require(all(not confirmed[i+3]or confirmed[i:i+3]==opaque[i:i+3]for i in range(0,len(confirmed),4)),'OAM reconstruction differs from original video')
    require(any(rendered[3::4]),'Empty native animation')
    return bytes(rendered)


def validate_tables(tables):
    require(tables.get('schema')=='tk2-native-siege-tables-v1' and tables.get('rom_sha256')==ROM_SHA,'Invalid native siege tables')
    chunks=tables.get('source_chunks',{})
    require(set(chunks)==set(TABLE_HASHES),'Missing native table chunks')
    native={}
    for key,expected in TABLE_HASHES.items():
        row=chunks[key]
        try: raw=bytes.fromhex(row['hex']);cpu=int(row['cpu'],16)
        except (KeyError,ValueError,TypeError) as error: raise ValueError('Invalid source chunk') from error
        require(row['sha256']==sha(raw)==expected and row['bytes']==len(raw),'Native source chunk changed: '+key)
        require(row['file_offset']==16+row['physical_bank']*8192+(cpu&8191),'Native table offset mismatch')
        native[key]=raw
    formations=tables.get('formations',[])
    require(len(formations)==6,'Six original formation tables required')
    for index,row in enumerate(formations):
        for axis in ('x','y'):
            pointer=int.from_bytes(native['formation_'+axis+'_pointers'][2*index:2*index+2],'little')
            start=int(chunks['formation_'+axis]['cpu'],16)
            expected=list(native['formation_'+axis][pointer-start:pointer-start+11])
            require(row.get('index')==index and row.get(axis+'ptr')==hex(pointer) and row.get(axis)==expected,'Formation differs from native source table')
        require(all(0<=x<=15 and 0<=y<=9 for x,y in zip(row['x'],row['y'])),'Formation exceeds 16x10 field')
    require(tables.get('ratios_B7AC')==list(native['troop_type_thresholds']),'Troop type thresholds differ from native source')
    require(tables.get('action_type_order')==list(native['action_type_order']),'Action type order differs from native source')
    castle=tables.get('castle_layout',{})
    require(castle.get('physical_bank')==1 and castle.get('cpu')=='8A30' and castle.get('background')==5,'Invalid castle layout origin')
    require(castle.get('raw')==list(native['castle_layout']) and castle.get('terrain_class_lut')==list(native['terrain_classes']),'Castle data differs from native source')
    classes=[[native['terrain_classes'][value] for value in native['castle_layout'][y*16:(y+1)*16]] for y in range(10)]
    require(castle.get('classes')==classes,'Castle collision classes differ from native source')
    return {'formations':6,'table_bytes':sum(map(len,native.values())),'castle_wall_cells':sum(v==5 for row in classes for v in row)}


def validate(data, read):
    require(data.get('schema')=='tk2-original-siege-assets-v1','Invalid siege asset schema')
    require(data.get('rom_sha256')==ROM_SHA and data.get('core_sha256')==CORE_SHA,'Original ROM/core identity mismatch')
    require(data.get('controlled_fixture')is True and data.get('natural_gameplay')is False,'Capture must disclose controlled fixture')
    require(all(data.get('runtime_requires_'+name)is False for name in ('rom','archive','emulator')),'Runtime must not require original inputs')
    encoded=json.dumps(data,ensure_ascii=False)
    require('/Users/'not in encoded and '/tmp/'not in encoded,'Public manifest exposes local absolute paths')
    table_row=data.get('data',{}).get('native_tables',{})
    raw=read(public_path(table_row.get('path')))
    require(sha(raw)==table_row.get('sha256'),'Native tables file hash mismatch')
    tables=json.loads(raw)
    require(data.get('tables')==tables,'Inline tables and published data differ')
    counts=validate_tables(tables)
    records={};decoded={};sizes={}
    assets=data.get('assets',{});captures=data.get('captures',{})
    require(isinstance(assets,dict) and isinstance(captures,dict) and set(captures)==set(CAPTURE_HASHES),'Required native captures missing')
    for rows in (captures,assets):
        for key,row in rows.items():
            path=public_path(row.get('path'));blob=read(path)
            require(path not in records,'Duplicate public asset path')
            require(isinstance(row.get('sha256'),str) and HEX.fullmatch(row['sha256']) and sha(blob)==row['sha256'],'Siege asset hash mismatch: '+key)
            size=(row.get('width'),row.get('height'));decoded[path]=pixels(blob,size);sizes[path]=size;records[path]=row
            if rows is captures:require(row['sha256']==CAPTURE_HASHES[key] and size==(256,240),'Native capture anchor mismatch')
    provenances={}
    for row in data.get('source_provenance',[]):
        path=public_path(row.get('path'));blob=read(path)
        require(sha(blob)==row.get('sha256') and HEX.fullmatch(row.get('original_sha256','')),'Capture provenance hash mismatch')
        value=json.loads(blob)
        require('/Users/'not in blob.decode() and '/tmp/'not in blob.decode(),'Provenance exposes local absolute paths')
        require(value.get('rom_sha256')==ROM_SHA and value.get('rom_modified')is False and value.get('core',{}).get('core_sha256')==CORE_SHA,'Capture provenance ROM/core mismatch')
        require(value.get('controlled_fixture')is True and value.get('natural_gameplay')is False,'Capture provenance must disclose fixture')
        if row['source_id']=='retained-original-field':
            require(value.get('schema')=='tk2-retained-original-capture-reference-v1' and value.get('captured_frame')==1155,'Invalid retained original field capture')
        else:
            require(any(step.get('background')==5 for step in value.get('steps',[])),'No native castle execution evidence')
        provenances[row['source_id']]=value
    require(len(provenances)==4,'Native castle, field and animation provenance required')
    require(len(provenances['native-soldier-animation']['changes'])==4,'Native animation order fixture must be disclosed')
    require(len(provenances['controlled-capture-run3']['changes'])==6 and provenances['controlled-capture-actions']['changes']==[],'Native RAM fixture modifications must remain disclosed')
    for key,row in captures.items():
        provenance=provenances.get(row.get('source_id'),{})
        output=provenance.get('outputs',{}).get(row.get('capture_label','')+'.png',{})
        require(output.get('sha256')==row['sha256'],'Capture is not backed by native provenance output')
    four=0;verified=0;candidates=0
    for key,row in assets.items():
        source=row.get('source',{});operations=source.get('operations',[])
        if 'asset' in source:
            origin=public_path(source['asset']);require(origin in records and records[origin]['sha256']==source.get('asset_sha256'),'Missing source asset')
            expected,size=decoded[origin],sizes[origin]
        else:
            origin=public_path(source.get('screenshot'));require(origin in records and records[origin]['sha256']==source.get('screenshot_sha256'),'Missing native screenshot source')
            expected,size=crop(decoded[origin],sizes[origin],source.get('source_rect'))
        for operation in operations:
            kind=operation.get('kind')
            if kind=='nearest_exact_4x':expected=nearest4(expected,size);size=(size[0]*4,size[1]*4);four+=1
            elif kind=='native_oam_animation_reconstruction':
                require(row.get('classification')=='native-oam-animation-sprite'and row.get('clean_sprite_verified')is True,'Original OAM art must be explicitly verified')
                expected=animation_sprite(key,operation,expected,size)
            elif kind=='native_chr_background_index_transparency':
                require(size==(16,16) and row.get('clean_sprite_verified')is True and row.get('classification')=='verified-native-chr-sprite','Native sprite verification must be explicit')
                expected=native_sprite(key,operation,expected)
            elif kind=='pixel_exact_native_background_difference':
                background=public_path(operation.get('background'));require(background in records and records[background]['sha256']==operation.get('background_sha256'),'Missing original background')
                base,base_size=crop(decoded[background],sizes[background],source.get('source_rect'))
                require(base_size==size,'Difference background size mismatch')
                result=bytearray(expected)
                for offset in range(0,len(result),4):result[offset+3]=0 if expected[offset:offset+3]==base[offset:offset+3] else 255
                expected=bytes(result)
                require(row.get('classification')=='retained-background-difference-candidate' and row.get('clean_sprite_verified')is False and row.get('runtime_eligible')is False,'Unverified difference layer cannot be advertised as a clean runtime sprite')
                candidates+=1
            else:raise ValueError('Unknown image operation')
        require(sizes[row['path']]==size and decoded[row['path']]==expected,'Native crop/derivative pixel mismatch: '+key)
        verified+=size[0]*size[1]
    require(all(name in assets for name in ['siege-background','siege-background-4x','witness-siege-formation',*[f'formation-{i}'for i in range(4)]]),'Required original art missing')
    require(set(CHR_HASHES).issubset(assets),'Eight clean original unit types required')
    for key in CHR_HASHES:
        kind,side=key.removeprefix('native-sprite-').split('-')
        for frame in range(2):
            row=assets.get(f'sprite-{kind}-{side}-{frame}',{})
            require(row.get('clean_sprite_verified')is True and row.get('single_native_pose_reused')is True and row.get('pose_variant')==0 and row.get('requested_frame')==frame,'Reused native pose must not be claimed as a separately captured action')
    return {**counts,'pngs':len(records),'exact4x':four,'clean_native_sprites':8,'native_walking_frames':16,'native_attack_effects':2,'difference_candidates_not_sprites':candidates,'pixels_checked':verified,'checker_requires_rom':False}


def check(root=OUT):
    root=Path(root)
    data=json.loads(safe_read(root,PREFIX+'index.json'))
    result=validate(data,lambda path:safe_read(root,path))
    expected={'index.json'}|{Path(row['path']).name for group in (data['assets'],data['captures'],data['data']) for row in group.values()}|{Path(row['path']).name for row in data['source_provenance']}
    require({p.name for p in root.iterdir()}==expected,'Unexpected or missing siege source files')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=OUT)
    args=parser.parse_args()
    print(json.dumps(check(args.root),sort_keys=True))
