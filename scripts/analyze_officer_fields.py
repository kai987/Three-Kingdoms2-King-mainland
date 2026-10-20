#!/usr/bin/env python3
"""Extract code/glyph evidence for officer fields, without modifying the ROM."""
from pathlib import Path
import argparse,json,hashlib,sys,csv
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source/recovered'))
from officers import ROM_SHA256,initial_officers,WEAPON_NAMES,ARMOR_NAMES

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'analysis/officer_fields');a=p.parse_args()
    blob=a.rom.read_bytes()
    if hashlib.sha256(blob).hexdigest()!=ROM_SHA256:raise ValueError('Different ROM')
    out=a.out;out.mkdir(parents=True,exist_ok=True)
    def evidence(bank,cpu,size,description):
        base=0xe000 if bank==31 else (0xa000 if bank in (8,10,12,14,23,25,27,29) else 0xc000)
        off=16+bank*8192+cpu-base
        return {'bank':bank,'cpu_address':f'0x{cpu:04X}','rom_offset':f'0x{off:06X}','raw_hex':blob[off:off+size].hex(' ').upper(),'description':description}
    fields=[]
    for offset,label,name in [(0,'体','health'),(1,'武','martial_strength'),(2,'知','intellect'),(3,'忠','loyalty'),(4,'徳','virtue')]:
        fields.append({'offset':offset,'size':1,'name':name,'ui_label':label,'status':'confirmed','evidence':[evidence(29,0xbb70,40,'Offsets0..3 rendered sequentially at RAM018B,018E,0191,0194') if offset<4 else evidence(29,0xbba4,15,'Offset4 rendered at RAM0197')],'notes':['Loyalty100 is rendered as -- at bank29 BC32 and bank25 B627.'] if offset==3 else []})
    fields.extend([
      {'offset':5,'size':1,'name':'roaming_city_id','status':'strong inference','evidence':[evidence(8,0xbd2b,44,'Clear status low2 and assign byte5 from city/adjacent-city selection'),evidence(26,0xc099,15,'Clear status low2 and store city index $040E into byte5'),evidence(25,0xba14,65,'Search status0 officers; exclude byte5 matching current/neighbor city')],'notes':['Initial byte5 is0 for every officer. The location becomes meaningful in status0 transitions.']},
      {'offset':6,'size':2,'name':'experience_raw','ui_label':'経','status':'confirmed','evidence':[evidence(29,0xbbb3,54,'Read LE16, multiply by2, discard low2 decimal digits for display'),evidence(15,0xd807,128,'Add reward/2 to experience, update experience tier and martial strength')],'notes':['Displayed experience = floor(raw/50) for normal raw0..49999. The three-digit UI drops higher digits for abnormal values. Shared experience helper is reconstructed and tested in battle.py.']},
      {'offset':8,'size':2,'name':'troops_raw','ui_label':'兵','status':'confirmed','evidence':[evidence(29,0xbbf4,33,'Display byte8 plus low2 bits of byte9'),evidence(25,0xb663,54,'Render the same masked soldier count')],'notes':['Arithmetic often reads the full LE16 word; UI masks it to10 bits. Meaning of byte9 upper6 bits remains unresolved.']},
      {'offset':9,'bits':'2..7','name':'troops_upper_unresolved_bits','status':'unresolved','evidence':[evidence(25,0xb66a,9,'Read byte9 and mask upper6 bits out of displayed troop count')],'notes':['Retained in troops_raw; no invented status flag semantics.']},
      {'offset':10,'bits':'0..4','name':'weapon_id','status':'confirmed','evidence':[evidence(25,0xb730,71,'Use low5 to select equipment records0..23'),evidence(25,0xb7c1,24,'Equipment pointer table bank16 $9B12')],'notes':['Decoded item glyph records contain swords, blades and polearms. Raw low5 values24..31 have no confirmed weapon meaning.']},
      {'offset':10,'bits':'5..7','name':'armor_id','status':'confirmed','evidence':[evidence(25,0xb74c,47,'Extract high3, add24 and select armor equipment record')],'notes':['Items24..31 visually read as armor/headgear/clothing; not horses.']},
      {'offset':11,'bits':'0..1','name':'status_code','status':'strong inference','encoding_status':'confirmed','evidence':[evidence(25,0xaf00,30,'Status1 waits for scripted year eligibility'),evidence(25,0xaf3f,22,'Insert officer into city roster then set status2'),evidence(26,0xc099,15,'Remove affiliation and set status0 with location'),evidence(25,0xbdc6,8,'Set status3 before removal from city roster')],'interpretation':{'0':'unaffiliated / roaming','1':'pending scripted appearance','2':'assigned to city roster','3':'removed / defeated / unavailable'},'notes':['Status3 is used after defeat and removal; permanent death vs recoverable removal is context dependent.']},
      {'offset':11,'bits':'2..3','name':'terrain_affinity_code','status':'strong inference','glyph_status':'confirmed','evidence':[evidence(25,0xb630,29,'Select top glyph tiles62/64/60 by bits2..3'),evidence(25,0xb64d,22,'Select bottom glyph tiles72/74/70')],'glyph_mapping':{'0':'平','1':'山','2':'水'},'notes':['Code3 is unused in initial table and runs beyond the3-entry UI selector. These are terrain categories, not cavalry/archer IDs.']},
      {'offset':11,'bits':'4..7','name':'experience_tier','ui_label':'レベル','status':'confirmed','evidence':[evidence(25,0xb5a6,36,'Display (byte11>>4)+1'),evidence(15,0xd838,120,'Read current experience tier, compare thresholds and preserve low4 when incrementing')],'notes':['Internal tier0 means displayed level1. Thresholds1000,2000,3500,5000,7500,10000,15000; at most one tier gained per helper invocation.']},
    ])
    # Keep the phase5 producer evidence reproducible when rebuilding the schema.
    for field in fields:
        if field['name'] == 'troops_raw':
            field['notes'] = ['Officer-list display is low10; readers/writers differ by path. See phase5 troop evidence.']
        if field['name'] == 'troops_upper_unresolved_bits':
            field['semantic_status'] = 'numeric overflow producer confirmed; independent flag semantics unresolved'
            field['phase5_evidence'] = '../phase5/troops/evidence.json'
            field['phase5_core_fixture'] = '../phase5/troops/core-fixture/validation.json'
            field['notes'] = ['Original garrison allocation can produce raw1098 (0x044A), displayed low10=74 and upper6=1.', 'Upper bits are preserved by some writers, cleared by others and treated as full16-bit numeric storage by reserve/attrition paths.', 'No independent training or status flag name is assigned.']
    palette=[255,170,85,0]
    def tile(bank,code):
        off=0x40010+bank*1024+code*16;raw=blob[off:off+16]
        image=Image.new('L',(8,8));pix=image.load()
        for y in range(8):
            for x in range(8):pix[x,y]=palette[((raw[y]>>(7-x))&1)|(((raw[y+8]>>(7-x))&1)<<1)]
        return image
    def glyph(bank,codes):
        im=Image.new('L',(16,16),255)
        for i,c in enumerate(codes):im.paste(tile(bank,c),((i%2)*8,(i//2)*8))
        return im
    labels=[('体',[0,1,16,17]),('武',[4,5,20,21]),('知',[2,3,18,19]),('忠',[8,9,24,25]),('徳',[6,7,22,23]),('経',[10,11,26,27]),('兵',[38,39,40,41])]
    sheet=Image.new('L',(700,100),240);draw=ImageDraw.Draw(sheet)
    for i,(label,codes) in enumerate(labels):
        sheet.paste(glyph(6,codes).resize((64,64),Image.Resampling.NEAREST),(100*i,25));draw.text((100*i,0),f'byte group {i}',fill=0)
    sheet.save(out/'field-labels-chr06.png')
    terrain=Image.new('L',(300,100),240);draw=ImageDraw.Draw(terrain)
    for i,c in enumerate([34,36,32]):
        terrain.paste(glyph(6,[c,c+1,c+16,c+17]).resize((64,64),Image.Resampling.NEAREST),(100*i,25));draw.text((100*i,0),f'code {i}',fill=0)
    terrain.save(out/'terrain-affinity-glyphs-chr06.png')
    equipment=[]
    for i in range(32):
        ptr_offset=0x21b22+2*i;cpu=0x8000+int.from_bytes(blob[ptr_offset:ptr_offset+2],'little');off=0x20010+cpu-0x8000
        raw=blob[off:off+17];im=Image.new('L',(64,16),255)
        for j,t in enumerate(raw[1:]):
            if t!=1:im.paste(tile(raw[0],t&63),((j%8)*8,(j//8)*8))
        image_name=f'equipment-{i:02d}.png';im.resize((256,64),Image.Resampling.NEAREST).save(out/image_name)
        equipment.append({'item_id':i,'kind':'weapon' if i<24 else 'armor','observed_name':WEAPON_NAMES[i] if i<24 else ARMOR_NAMES[i-24],'transcription_status':'manually transcribed from rendered ROM glyphs; original pixels retained','weapon_id':i if i<24 else None,'armor_id':i-24 if i>=24 else None,'pointer_rom_offset':f'0x{ptr_offset:06X}','record_rom_offset':f'0x{off:06X}','cpu_address':f'0x{cpu:04X}','chr_1k_bank':raw[0],'raw_hex':raw.hex(' ').upper(),'image':image_name})
    for start in range(0,32,8):
        sheet=Image.new('L',(512,8*84),240);draw=ImageDraw.Draw(sheet)
        for i in range(start,start+8):
            y=(i-start)*84;draw.text((0,y),f'item{i:02d} {equipment[i]["cpu_address"]}',fill=0);sheet.paste(Image.open(out/equipment[i]['image']),(160,y))
        sheet.save(out/f'equipment-names-{start:02d}-{start+7:02d}.png')
    payload={'rom_sha256':ROM_SHA256,'record_size':12,'record_count':237,'fields':fields,'label_template_evidence':[evidence(29,0xb909,64,'Columns11,14,17,20,23,26 label offsets0,1,2,3,4,6 as体武知忠徳経'),evidence(29,0xb849,64,'Alternative mode columns label体武知忠経兵')],'equipment':equipment,'limitations':['Labels are extracted from original CHR pixels; script does not use OCR to invent names.','Synthetic py65 field mutation tests are separate from unchanged-ROM Nestopia screenshots.','Byte5 semantics, status labels and terrain affinity interpretation retain explicit inference status.']}
    (out/'fields.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    officers=initial_officers(blob)
    keys=['id','rom_offset','health','martial_strength','intellect','loyalty','virtue','roaming_city_id','experience_raw','experience_display','troops_raw','troops_display','troops_upper_unresolved_bits','weapon_id','weapon_name','armor_id','armor_name','status_code','terrain_affinity_code','terrain_glyph','experience_tier','level_display','raw_hex']
    with (out/'officers-decoded.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        for i,o in enumerate(officers):
            row={'id':i,'rom_offset':f'0x{0x22010+i*12:06X}','raw_hex':o.raw.hex(' ').upper()}
            row.update({k:getattr(o,k) for k in keys if hasattr(o,k)});writer.writerow(row)
    print(f'Wrote field evidence,237 decoded records and32 equipment glyph records to {out}')

if __name__=='__main__':main()
