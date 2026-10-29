#!/usr/bin/env python3
"""Build a separate, source-labelled static officer troop-type policy.

No people, compiled campaigns, original records or saves are rewritten. The
retained237 ROM records suffice for CI; --rom additionally checks the user's
exact ROM. Original byte11 data wins over a conflicting third-party table.
"""
from collections import Counter
from hashlib import sha256
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'game/config/references/officer-troop-types-v1.json'
ROM_SOURCE='game/config/references/original-officer-stats.json'
CN_SOURCE='game/config/references/cnblogs-officer-stats.json'
PEOPLE_SOURCE='game/config/campaigns/people.json'
REGION_SOURCE='game/config/campaigns/shared.json'
ROM_SOURCE_SHA='11ab9fbfe6852d2d8e59a400e7fd62b59281506b224acef141d2690e4a769032'
CN_SOURCE_SHA='fee9b0e47615f676c25bea80900bdb60896a193253f4eb8e4a9c4e3ed8605fef'
RULES_VERSION='officer-troop-types-v1'
KINDS=[dict(code=0,key='plain',label_tc='平',label_ja='平'),
       dict(code=1,key='mountain',label_tc='山',label_ja='山'),
       dict(code=2,key='water',label_tc='水',label_ja='水')]
# Historical careers inform these remake choices, not original-game numbers.
# Names assert the stable person binding; they are never used for fuzzy joins.
TRAITS={
 'san14-candidate-0134':('贺齐',1,'https://zh.wikisource.org/zh-hant/三國志/卷60','長期平定山越、攻討山地險阻。'),
 'san14-candidate-0900':('陆抗',2,'https://zh.wikisource.org/zh-hant/三國志/卷58','長江上游軍務與西陵方面作戰。'),
 'san14-candidate-0726':('陶璜',2,'https://zh.wikisource.org/zh-hant/晉書/卷057','率軍從海道進入交趾。'),
 'san14-candidate-0290':('吾彦',2,'https://zh.wikisource.org/zh-hant/晉書/卷057','建平守備、鐵鎖橫斷江路以抗舟師。'),
 'san14-candidate-0060':('王濬',2,'https://zh.wikisource.org/zh-hant/晉書/卷042','益州造艦、率舟師順江伐吳。'),
 'san14-candidate-0742':('唐彬',2,'https://zh.wikisource.org/zh-hant/晉書/卷042','監巴東軍事，參與順江伐吳。'),
 'san14-candidate-0773':('马隆',1,'https://zh.wikisource.org/zh-hant/晉書/卷057','率輕兵平涼州，因地形穿越險阻。'),
}


def encoded(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()


def compact_digest(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def load(relative,*,expected=None):
    raw=(ROOT/relative).read_bytes()
    if expected and sha256(raw).hexdigest()!=expected:
        raise ValueError('Reviewed troop-type source changed: '+relative)
    return json.loads(raw),sha256(raw).hexdigest()


def build(*,rom=None):
    original,original_sha=load(ROM_SOURCE,expected=ROM_SOURCE_SHA)
    external,external_sha=load(CN_SOURCE,expected=CN_SOURCE_SHA)
    pool,pool_sha=load(PEOPLE_SOURCE)
    shared,shared_sha=load(REGION_SOURCE)
    people=pool['people'];region=shared['catalog']
    cities={row['id']:row for row in region['cities']}
    if original['record_size']!=12 or original['original_records']!=237 or len(original['records'])!=237:
        raise ValueError('Expected original237 twelve-byte records')
    raw_rom=Path(rom).read_bytes()if rom else None
    if raw_rom is not None and sha256(raw_rom).hexdigest()!=original['rom_sha256']:
        raise ValueError('Different original ROM')
    records={};rom_records=[]
    for row in original['records']:
        raw=bytes.fromhex(row['record_hex']);index=row['original_id']
        if (len(raw)!=12 or row['rom_offset']!=original['record_offset']+index*12
                or sha256(raw).hexdigest()!=row['record_sha256']):
            raise ValueError('Invalid retained original troop record')
        if raw_rom is not None and raw_rom[row['rom_offset']:row['rom_offset']+12]!=raw:
            raise ValueError('Retained troop record differs from ROM')
        code=(raw[11]>>2)&3
        evidence=dict(original_id=index,person_id=row['person_id'],raw_code=code,
            byte11=raw[11],rom_offset=row['rom_offset']+11,record_sha256=row['record_sha256'])
        rom_records.append(evidence)
        pid=row['person_id']
        if pid is None:
            continue
        if pid not in people or pid in records:
            raise ValueError('Unreviewed or duplicate original troop identity')
        # The original unnamed code3 has no known producer and must never
        # expose its adjoining-table/zero-movement-cost bug as a fourth type.
        if code==3:
            raise ValueError('Original code3 needs an explicit reviewed normalization')
        records[pid]=dict(person_id=pid,name=people[pid]['name'],code=code,
            source_kind='verified_original_rom',reference=ROM_SOURCE,
            original_id=index,raw_code=code,byte11=raw[11],rom_offset=row['rom_offset']+11,
            record_sha256=row['record_sha256'],
            basis_tc='本機原版武將記錄第11位元組的bits2–3。',
            basis_ja='手元の原作武将記録のバイト11・ビット2～3。')
    conflicts=[]
    for row in external['records']:
        pid=row.get('person_id')
        if not pid:
            continue
        code={'平':0,'山':1,'水':2}[row['terrain_label']]
        if pid in records:
            if code!=records[pid]['code']:
                conflicts.append(dict(person_id=pid,name=people[pid]['name'],
                    original_id=records[pid]['original_id'],selected_rom_code=records[pid]['code'],
                    transcription_code=code,source_row_id=row['source_row_id'],
                    policy='Pinned local original ROM wins; retain disagreement without rewriting either source.'))
            continue
        if pid not in people:
            raise ValueError('Unknown reviewed transcription identity')
        records[pid]=dict(person_id=pid,name=people[pid]['name'],code=code,
            source_kind='original_table_transcription',reference=CN_SOURCE,
            source_row_id=row['source_row_id'],source_line_sha256=row['source_line_sha256'],
            basis_tc='已審核身分的原版公開武將表轉錄；未宣稱已閉合本機ROM槽位。',
            basis_ja='身元照合済みの公開原作武将表の転記。手元ROMのスロット照合済みとは扱いません。')
    for pid,person in people.items():
        base=person['profile']['terrain_affinity']
        if type(base)is not int or base not in (0,1,2):
            raise ValueError('Invalid baseline troop type')
        if pid in records:
            records[pid]['base_code']=base
            continue
        trait=TRAITS.get(pid)
        city_id=region['appearance_locations'].get(pid)
        city=cities.get(city_id)
        row=dict(person_id=pid,name=person['name'],base_code=base)
        if trait:
            name,code,url,feature=trait
            if person['name']!=name:
                raise ValueError('Reviewed troop-trait identity changed')
            row.update(code=code,source_kind='design_trait_inference',reference=url,feature_tc=feature,
                basis_tc='依人物生涯或專長作本作軍種推定；史料不提供遊戲軍種數值。',
                basis_ja='人物の経歴・特長から本作で推定した兵種。史料にゲームの兵種数値があるわけではありません。')
        elif base in (1,2):
            row.update(code=base,source_kind='retained_design',reference=PEOPLE_SOURCE,
                basis_tc='延續既有明確軍種設計；未取得原版對照，不宣稱原值。',
                basis_ja='既存の明示的な兵種設定を維持。原作対照は未確認で、原作値とは表示しません。')
        elif city and city['terrain']in ('mountain','water'):
            row.update(code={'mountain':1,'water':2}[city['terrain']],source_kind='design_region_inference',
                reference=REGION_SOURCE,region_city=city_id,region_terrain=city['terrain'],
                basis_tc='依固定登場地區的山地或水域作靜態遊戲推定；不是史實能力值。',
                basis_ja='固定の登場地域の山地・水域から静的に推定したゲーム設定。史実の能力値ではありません。')
        else:
            row.update(code=base,source_kind='fallback_design',reference=PEOPLE_SOURCE,
                basis_tc='資料不足，保留既有軍種設定。',
                basis_ja='資料が不足するため、既存の兵種設定を維持します。')
        records[pid]=row
    if len(records)!=len(people) or len({row['original_id']for row in records.values()if row['source_kind']=='verified_original_rom'})!=221:
        raise ValueError('Troop-type coverage or reviewed ROM binding changed')
    records=dict(sorted(records.items()))
    return dict(schema='tk2-officer-troop-types-v1',rules_version=RULES_VERSION,
        policy='Static stable person IDs. Verified local ROM values precede reviewed third-party transcription; new people use labelled career/region inference or retain baseline. No faction/date switch, martial-based guess, random assignment or saved-profile rewrite.',
        save_policy='Raw saved profile remains the baseline. Effective troop type changes future tactical movement and display under this explicit policy version; already frozen march quotations remain unchanged.',
        original_field=dict(record_size=12,record_offset=original['record_offset'],byte_index=11,bits=[2,3],formula='(byte11 >> 2) & 3',
            rom_sha256=original['rom_sha256'],unassigned_code3_policy='Never a free-movement fourth type; requires a separate reviewed normalization.'),
        kinds=KINDS,source_files={ROM_SOURCE:original_sha,CN_SOURCE:external_sha,PEOPLE_SOURCE:pool_sha,REGION_SOURCE:shared_sha},
        counts=dict(people=len(records),sources=dict(sorted(Counter(row['source_kind']for row in records.values()).items())),
            effective_codes={str(k):v for k,v in sorted(Counter(row['code']for row in records.values()).items())},
            changed_from_baseline=sum(row['code']!=row['base_code']for row in records.values()),
            original_records=237,bound_original=221),
        records_sha256=compact_digest(records),records=records,rom_records=rom_records,source_disagreements=conflicts)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--rom',type=Path)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args(argv)
    result=build(rom=args.rom);raw=encoded(result)
    if args.check:
        if args.output.read_bytes()!=raw:raise ValueError('Troop-type reference is stale')
    else:args.output.write_bytes(raw)
    print(json.dumps(result['counts'],ensure_ascii=False,sort_keys=True))


if __name__=='__main__':main()
