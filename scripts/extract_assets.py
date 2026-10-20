#!/usr/bin/env python3
"""Extract and browse NES CHR-ROM without changing the source ROM.

Outputs use a diagnostic greyscale palette. A cartridge's runtime palettes,
nametables, tile pairing and bank-switch state cannot be recovered from CHR
alone, so these images are evidence for tiles, not final game screenshots.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

PALETTE = [(255,255,255), (170,170,170), (85,85,85), (0,0,0)]
BANK_SIZE = 0x1000
TILES_PER_BANK = BANK_SIZE // 16
KNOWN_ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
NAME_TABLE_FILE_OFFSET = 0x22DC4
NAME_RECORD_COUNT = 237


def decode_tile(data: bytes) -> Image.Image:
    if len(data) != 16:
        raise ValueError('A NES tile needs 16 bytes')
    im = Image.new('RGB', (8,8))
    pix = im.load()
    for y in range(8):
        for x in range(8):
            bit = 7-x
            pix[x,y] = PALETTE[((data[y] >> bit) & 1) | (((data[y+8] >> bit) & 1) << 1)]
    return im


def render_bank(data: bytes) -> Image.Image:
    im = Image.new('RGB', (128,128), PALETTE[0])
    for t in range(len(data)//16):
        im.paste(decode_tile(data[t*16:(t+1)*16]), ((t%16)*8, (t//16)*8))
    return im


def labeled_sheet(im: Image.Image, bank: int) -> Image.Image:
    scale=4
    margin=40
    canvas=Image.new('RGB',(margin+512+10,margin+512+10),(240,240,240))
    draw=ImageDraw.Draw(canvas)
    draw.text((4,3),f'CHR bank {bank:02X}; absolute tile {bank*256:04X}-{bank*256+255:04X}', fill='black')
    canvas.paste(im.resize((512,512), Image.Resampling.NEAREST),(margin,margin))
    for r in range(16):
        draw.text((8,margin+r*32+10),f'{r:X}0',fill='black')
        draw.text((margin+r*32+12,24),f'{r:X}',fill='black')
    for pos in range(17):
        draw.line((margin+pos*32,margin,margin+pos*32,margin+512),fill=(210,140,140))
        draw.line((margin,margin+pos*32,margin+512,margin+pos*32),fill=(210,140,140))
    return canvas


def render_metatile_sheet(sheet: Image.Image, bank: int) -> Image.Image:
    """Visual grouping only: four spatially adjacent 8x8 tiles per cell."""
    out=Image.new('RGB',(8*82,8*92),(240,240,240))
    draw=ImageDraw.Draw(out)
    for i in range(64):
        source_x=i%8*16; source_y=i//8*16
        x=i%8*82; y=i//8*92
        cell=sheet.crop((source_x,source_y,source_x+16,source_y+16))
        out.paste(cell.resize((64,64),Image.Resampling.NEAREST),(x,y+20))
        first=bank*256+source_y//8*16+source_x//8
        draw.text((x,y),f'{first:04X}',fill='black')
    return out


def extract_name_glyphs(rom: bytes, chr_data: bytes, chr_start: int, out: Path) -> dict:
    """Game-specific names, justified by static code, not guessed tile layouts.

    PRG bank 26 $D2EA-$D342 reads 13-byte records at bank17 $8DB4.
    Record[0] is the 1 KiB bank written to N163 $9800 by fixed-bank31
    $FBF1: LDA $C1; STA $9800. Thus tilebyte+$C0 selects the PPU $0C00
    page but physical CHR is bank*1024 + tilebyte*16. No extra $C0.
    Remaining bytes are TL,TR,BL,BR for up to three 16x16 glyphs; $FF ends.
    """
    names_dir=out/'names'; names_dir.mkdir(exist_ok=True)
    glyph_dir=names_dir/'glyphs'; glyph_dir.mkdir(exist_ok=True)
    glyph_by_hash={}
    glyphs=[]
    names=[]
    for ident in range(NAME_RECORD_COUNT):
        record_offset=NAME_TABLE_FILE_OFFSET+ident*13
        record=rom[record_offset:record_offset+13]
        assert len(record)==13
        bank=record[0]
        codes=list(record[1:])
        count=codes.index(255) if 255 in codes else 12
        assert count%4==0, (ident,codes)
        assert all(c==255 for c in codes[count:]), (ident,codes)
        codes=codes[:count]
        assert all(c<64 for c in codes), (ident,codes)
        im=Image.new('RGB',(max(16,count//4*16),16),PALETTE[0])
        name_glyphs=[]
        for slot in range(count//4):
            group=codes[slot*4:slot*4+4]
            offsets=[bank*1024+c*16 for c in group]
            tile_data=[chr_data[o:o+16] for o in offsets]
            assert all(len(t)==16 for t in tile_data)
            combined=b''.join(tile_data)
            digest=hashlib.sha256(combined).hexdigest()
            cell=Image.new('RGB',(16,16))
            for quadrant, tile in enumerate(tile_data):
                cell.paste(decode_tile(tile),((quadrant%2)*8,(quadrant//2)*8))
            im.paste(cell,(slot*16,0))
            if digest not in glyph_by_hash:
                glyph_id=len(glyphs)
                glyph_by_hash[digest]=glyph_id
                path=glyph_dir/f'glyph-{glyph_id:03d}.png'
                cell.save(path)
                glyphs.append(dict(glyph_id=glyph_id,sha256=digest,image=str(path.relative_to(names_dir)),
                                   first_chr_bank_1k=bank,first_tile_codes=group,
                                   first_chr_relative_offsets=offsets,
                                   first_rom_file_offsets=[chr_start+o for o in offsets],references=[]))
            glyph_id=glyph_by_hash[digest]
            glyphs[glyph_id]['references'].append(dict(name_id=ident,position=slot))
            name_glyphs.append(dict(position=slot,glyph_id=glyph_id,tile_codes=group,
                                    chr_relative_offsets=offsets,rom_file_offsets=[chr_start+o for o in offsets]))
        path=names_dir/f'name-{ident:03d}.png'; im.save(path)
        names.append(dict(name_id=ident,record_file_offset=record_offset,record_hex=record.hex(' '),
                          chr_bank_1k=bank,chr_bank_file_start=chr_start+bank*1024,
                          glyph_count=count//4,width_pixels=im.width,height_pixels=im.height,
                          image=path.name,glyphs=name_glyphs,unicode_transcription=None))
    for glyph in glyphs:
        glyph['all_chr_adjacency_matches']=[]
    # Exact byte equality, not visual similarity/OCR. The 16-column atlas
    # adjacency is a candidate layout outside the confirmed name table.
    for first in range(len(chr_data)//16-17):
        if first%16==15:
            continue
        tiles=[first,first+1,first+16,first+17]
        digest=hashlib.sha256(b''.join(chr_data[t*16:t*16+16] for t in tiles)).hexdigest()
        if digest in glyph_by_hash:
            glyphs[glyph_by_hash[digest]]['all_chr_adjacency_matches'].append(
                dict(first_global_tile=first,global_tiles=tiles,
                     chr_relative_offsets=[t*16 for t in tiles],
                     rom_file_offsets=[chr_start+t*16 for t in tiles]))
    assert all(g['all_chr_adjacency_matches'] for g in glyphs)
    for first in range(0,NAME_RECORD_COUNT,64):
        subset=names[first:first+64]
        contact=Image.new('RGB',(8*208,((len(subset)+7)//8)*88),(240,240,240))
        draw=ImageDraw.Draw(contact)
        for pos, entry in enumerate(subset):
            x=pos%8*208+8; y=pos//8*88+4
            im=Image.open(names_dir/entry['image'])
            contact.paste(im.resize((im.width*4,64),Image.Resampling.NEAREST),(x,y+18))
            draw.text((x,y),f"ID {entry['name_id']:03d}  CHR {entry['chr_bank_1k']:02X}",fill='black')
        contact.save(names_dir/f"contact-{first:03d}-{first+len(subset)-1:03d}.png")
    glyph_sheet=Image.new('RGB',(16*78,((len(glyphs)+15)//16)*88),(240,240,240))
    draw=ImageDraw.Draw(glyph_sheet)
    for pos,glyph in enumerate(glyphs):
        x=pos%16*78+4;y=pos//16*88+4
        im=Image.open(names_dir/glyph['image'])
        glyph_sheet.paste(im.resize((64,64),Image.Resampling.NEAREST),(x,y+18))
        draw.text((x,y),f'G{pos:03d}',fill='black')
    glyph_sheet.save(names_dir/'glyph-overview.png')
    result=dict(record_count=NAME_RECORD_COUNT,record_size=13,table_file_start=NAME_TABLE_FILE_OFFSET,
                table_file_end_exclusive=NAME_TABLE_FILE_OFFSET+NAME_RECORD_COUNT*13,
                mapper_chr_bank_unit=1024,unique_glyphs=len(glyphs),
                confidence='static code and visible decoded glyphs; no OCR or Unicode claim',
                names=names,glyphs=glyphs)
    (names_dir/'name-glyph-index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    cards='\n'.join(f'''<article data-id="{e['name_id']}"><h2>ID {e['name_id']:03d} / 0x{e['name_id']:02X}</h2><img src="{e['image']}" width="{e['width_pixels']*4}" height="64" alt="ROM name glyph ID {e['name_id']}"><p>记录偏移 0x{e['record_file_offset']:06X}<br>1 KiB CHR bank 0x{e['chr_bank_1k']:02X}<br>字形编号：{', '.join('G'+str(g['glyph_id']).zfill(3) for g in e['glyphs'])}</p></article>''' for e in names)
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>武将名称字形记录</title><style>body{font:16px system-ui;margin:32px auto;padding:0 20px;max-width:1400px;background:#f5f5f2;color:#181818}header{max-width:1000px}p{line-height:1.7}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px}article{background:white;border:1px solid #ccc;padding:16px}h2{font-size:18px}img{image-rendering:pixelated;max-width:100%;object-fit:contain;object-position:left}input{font:inherit;padding:6px;margin:20px}a{color:#174da8}</style><header><h1>237 条名称字形记录</h1><p>根据 ROM 的名称绘制代码，恢复每条记录最多三个 16×16 汉字。此处直接显示原始像素，不用 OCR 猜测文字。字形编号按四个 tile 的原始 64 字节 SHA-256 去重，相同编号表示逐字节完全相同。</p><p>记录位置：PRG bank 17 CPU $8DB4，文件 0x022DC4；每条 13 字节。首字节是 1 KiB CHR bank，后 12 字节按左上、右上、左下、右下组成字形，0xFF 结束。物理 CHR 偏移 = bank × 1024 + tilebyte × 16。</p><p><a href="../index.html">全部 CHR 资源</a> · <a href="name-glyph-index.json">名称与字形精确索引</a> · <a href="glyph-overview.png">去重字形总览</a></p><p><a href="contact-000-063.png">ID 000–063</a> · <a href="contact-064-127.png">ID 064–127</a> · <a href="contact-128-191.png">ID 128–191</a> · <a href="contact-192-236.png">ID 192–236</a></p><label>按十进制 ID 筛选：<input id="filter" inputmode="numeric" placeholder="例如 2"></label></header><main class="grid">'''+cards+'''</main><script>document.querySelector('#filter').addEventListener('input',e=>{let q=e.target.value.trim();document.querySelectorAll('article').forEach(a=>a.hidden=q&&a.dataset.id!==q);});</script></html>'''
    (names_dir/'index.html').write_text(html)
    return {k:v for k,v in result.items() if k not in ('names','glyphs')}


def verify_outputs(source: Path, rom: bytes, out: Path, meta: dict) -> dict:
    """Validate artifacts against source bytes and independent decoder fixtures."""
    chr_start=meta['chr_file_start']
    assert (out/'chr.bin').read_bytes()==rom[chr_start:chr_start+meta['chr_size']]
    assert b''.join((out/b['binary']).read_bytes() for b in meta['banks'])==(out/'chr.bin').read_bytes()
    pngs=list(out.rglob('*.png'))
    for path in pngs:
        with Image.open(path) as im:
            im.verify()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==meta['source_sha256']
    assert set(decode_tile(bytes([255]*8+[0]*8)).getdata())=={PALETTE[1]}
    assert set(decode_tile(bytes([0]*8+[255]*8)).getdata())=={PALETTE[2]}
    fixture=decode_tile(bytes([0x80]+[0]*15))
    assert fixture.getpixel((0,0))==PALETTE[1] and fixture.getpixel((7,0))==PALETTE[0]
    result=dict(verified=True,source_sha256=meta['source_sha256'],chr_bytes=meta['chr_size'],
                chr_banks=len(meta['banks']),png_count=len(pngs),
                checks=['source ROM hash unchanged','CHR exact bytes and 64-bank concatenation',
                        'all PNGs decode','NES 2bpp low/high plane and MSB-left fixtures'])
    if 'names' in meta:
        index=json.loads((out/'names/name-glyph-index.json').read_text())
        assert len(list((out/'names').glob('name-*.png')))==NAME_RECORD_COUNT
        assert len(list((out/'names/glyphs').glob('glyph-*.png')))==len(index['glyphs'])
        for name in index['names']:
            with Image.open(out/'names'/name['image']) as im:
                assert im.size==(name['width_pixels'],16)
                for glyph in name['glyphs']:
                    for quadrant,offset in enumerate(glyph['rom_file_offsets']):
                        tile=decode_tile(rom[offset:offset+16])
                        x=glyph['position']*16+(quadrant%2)*8; y=(quadrant//2)*8
                        assert im.crop((x,y,x+8,y+8)).tobytes()==tile.tobytes()
        assert all(g['all_chr_adjacency_matches'] for g in index['glyphs'])
        result.update(name_records=len(index['names']),
                      name_glyph_positions=sum(len(n['glyphs']) for n in index['names']),
                      unique_glyph_patterns=len(index['glyphs']),
                      name_image_width_counts={str(w):sum(n['width_pixels']==w for n in index['names']) for w in [32,48]})
        result['checks'].extend(['name images match exact source tile quadrants',
                                 'all unique glyphs have exact CHR adjacency matches'])
    (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom',type=Path)
    parser.add_argument('--output',type=Path,default=Path('analysis/assets'))
    args=parser.parse_args()
    data=args.rom.read_bytes()
    if len(data)<16 or data[:4]!=b'NES\x1a':
        raise SystemExit('Not an iNES ROM')
    h=data[:16]
    if (h[7]&0x0c)==0x08:
        raise SystemExit('NES 2.0 size extensions are not implemented in this extractor')
    trainer_size=512 if h[6]&4 else 0
    prg_size=h[4]*16384
    chr_size=h[5]*8192
    chr_start=16+trainer_size+prg_size
    if len(data)<chr_start+chr_size:
        raise SystemExit('ROM is truncated')
    chr_data=data[chr_start:chr_start+chr_size]
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    banks_dir=out/'chr-banks'; banks_dir.mkdir(exist_ok=True)
    sheets_dir=out/'tile-sheets'; sheets_dir.mkdir(exist_ok=True)
    grouped_dir=out/'metatile-previews'; grouped_dir.mkdir(exist_ok=True)
    (out/'chr.bin').write_bytes(chr_data)
    bank_count=(chr_size+BANK_SIZE-1)//BANK_SIZE
    overview=Image.new('RGB',(8*168,((bank_count+7)//8)*172),(245,245,245))
    ov=ImageDraw.Draw(overview)
    entries=[]
    unique=set()
    blank_tiles=0
    for t in range(chr_size//16):
        tile=chr_data[t*16:(t+1)*16]
        unique.add(tile)
        if len(set(tile))==1 and tile[0] in (0,255):
            blank_tiles+=1
    for bank in range(bank_count):
        b=chr_data[bank*BANK_SIZE:(bank+1)*BANK_SIZE]
        binary=banks_dir/f'bank-{bank:02x}.chr'
        binary.write_bytes(b)
        sheet=render_bank(b)
        native=sheets_dir/f'bank-{bank:02x}-native.png'
        large=sheets_dir/f'bank-{bank:02x}.png'
        sheet.save(native)
        labeled_sheet(sheet,bank).save(large)
        if bank in [0,1,5,*range(0x15,0x20),0x22,0x23,0x38]:
            render_metatile_sheet(sheet,bank).save(grouped_dir/f'bank-{bank:02x}-16x16.png')
        x=(bank%8)*168+4; y=(bank//8)*172+4
        overview.paste(sheet.resize((160,160),Image.Resampling.NEAREST),(x,y+8))
        ov.text((x,y-2),f'bank {bank:02X}  tile {bank*256:04X}', fill='black')
        entries.append(dict(bank=bank,bank_hex=f'{bank:02X}',chr_relative_offset=bank*BANK_SIZE,
                            rom_file_offset=chr_start+bank*BANK_SIZE,size=len(b),first_tile=bank*256,
                            last_tile=bank*256+len(b)//16-1,sha256=hashlib.sha256(b).hexdigest(),
                            binary=str(binary.relative_to(out)),image=str(large.relative_to(out)),
                            native_image=str(native.relative_to(out))))
    overview.save(out/'chr-overview.png')
    meta=dict(source=str(args.rom.resolve()),source_size=len(data),source_sha256=hashlib.sha256(data).hexdigest(),
              header_hex=h.hex(),mapper=(h[6]>>4)|(h[7]&0xf0),prg_size=prg_size,chr_size=chr_size,
              chr_file_start=chr_start,chr_sha256=hashlib.sha256(chr_data).hexdigest(),
              tile_count=chr_size//16,unique_tile_patterns=len(unique),uniform_00_ff_tiles=blank_tiles,
              bank_size=BANK_SIZE,diagnostic_palette_rgb=PALETTE,banks=entries)
    if meta['source_sha256']==KNOWN_ROM_SHA256:
        meta['names']=extract_name_glyphs(data,chr_data,chr_start,out)
    (out/'asset-index.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    cards='\n'.join(f'''<article data-bank="{e['bank_hex']}"><h2>Bank {e['bank_hex']} · tiles {e['first_tile']:04X}–{e['last_tile']:04X}</h2><p>ROM 0x{e['rom_file_offset']:06X}–0x{e['rom_file_offset']+e['size']-1:06X}</p><a href="{e['image']}"><img loading="lazy" src="{e['image']}" alt="Bank {e['bank_hex']} NES CHR tile sheet"></a><p><a href="{e['binary']}">原始 4 KiB CHR</a> · <a href="{e['native_image']}">原始像素图</a></p></article>''' for e in entries)
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>三国志2超级版 CHR 资源浏览器</title><style>body{font:16px system-ui;margin:32px auto;padding:0 20px;max-width:1500px;background:#f5f5f2;color:#181818}header{max-width:900px}h1{font-size:30px}p{line-height:1.7}label{display:block;margin:24px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:28px}article{background:white;border:1px solid #ccc;padding:12px}h2{font-size:18px}img{max-width:100%;height:auto;image-rendering:pixelated}input{font:inherit;padding:6px}a{color:#174da8}</style><header><h1>三国志2超级版：CHR-ROM 资源</h1><p>共 16,384 个 8×8 像素 tile，按 4 KiB 分为 64 组。图片使用诊断灰度色，不代表游戏实际配色。表格行列标签为组内 tile 的十六进制偏移。例如组 01 的行 20、列 3 对应全局 tile 0x0123。</p><p>绝对文件偏移 = 0x040010 + 全局 tile 编号 × 16。NES 2bpp 每 tile 的前 8 字节为低位平面，后 8 字节为高位平面。</p><p><a href="chr-overview.png">全部资源总览</a> · <a href="names/index.html">237 条名称字形</a> · <a href="asset-index.json">可机读偏移索引</a> · <a href="assets-notes.md">资源观察记录</a></p><label>按 Bank 筛选（00–3F）：<input id="filter" placeholder="例如 0A" maxlength="2"></label></header><main class="grid">'''+cards+'''</main><script>document.querySelector('#filter').addEventListener('input',e=>{let q=e.target.value.trim().toUpperCase();document.querySelectorAll('article').forEach(a=>a.hidden=q&&!a.dataset.bank.includes(q));});</script></html>'''
    (out/'index.html').write_text(html)
    verify_outputs(args.rom,data,out,meta)
    print(json.dumps({k:v for k,v in meta.items() if k!='banks'},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
