#!/usr/bin/env python3
"""Presentation-only names/pixel colors; all released campaign bytes stay fixed."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def build():
    plan=json.loads((ROOT/'expansion/map/city-map-city-sea-plan-v42.json').read_text())
    names={key:dict(row) for key,row in plan['stateSeatNaming']['overrides'].items()}
    names['wei']={'displayName':'邺','state':'冀州','role':'汉末冀州治所、曹操魏王都；保留魏郡节点',
        'source':'https://whly.hebei.gov.cn/c/2023-07-26/573174.html'}
    names['shanyang']={'displayName':'昌邑','state':'兖州','role':'汉末兖州治所；只更改显示城名，不模拟此后的州治迁移',
        'source':'https://jnmz.jining.gov.cn/art/2019/9/10/art_9455_2033181.html'}
    names['danyang']['before212']='秣陵'
    names['danyang']['name_source']='https://dfz.nanjing.gov.cn/gzdt/202403/t20240315_4186987.html'
    # This is the existing native eight-pixel sprite, enlarged to32px. Only
    # its white interior pixels are recolored; the original outline stays.
    pixels=[[x*4-16,y*4-16] for y,row in enumerate(plan['originalSprite']['rows'])
            for x,value in enumerate(row) if value==6]
    colors=dict(wei='#fcfcfc',shu='#f8b800',wu='#f85898',han='#fcfcfc',yellow_turban='#f8b800',
        yuan_shao='#a4e4fc',han_fu='#3cbcfc',liu_biao='#b8b8f8',liu_dai='#f878f8',
        liu_zhang='#00e8d8',liu_yan='#00e8d8',ma_teng='#fca044',yuan_shu='#f8d878',
        gongsun='#b8f818',gongsun_zan='#b8f818',liu_yu='#58d854',dong_zhuo='#f83800',
        li_jue='#f83800',sun_jian='#f85898',lubu='#f87858',zhang_chao='#fc7460',
        shi_xie='#94b0fc',zhang_yang='#d8b8f8',kong_rong='#58f898',tao_qian='#fcbcb0',
        liu_you='#f8d8f8',wang_lang='#f8b8f8',zhang_lu='#c8c8c8',neutral='#9c9c9c')
    result={'schema':'map-presentation-v1','city_names':names,'colors':colors,'castle_fill_pixels':pixels,
        'name_policy':'Use the approved board state-seat city labels; retain commandery IDs and original catalog names. These labels do not simulate every relocation of a provincial government.',
        'date_policy':'Match the original single-line year/month frame; preview chapter dates before starting.',
        'background':'/assets/map-clean.png',
        'background_sha256':hashlib.sha256((ROOT/'game/assets/map-clean.png').read_bytes()).hexdigest(),
        'source_html_sha256':hashlib.sha256((ROOT/'expansion/map/city-map-city-sea-preview-v42.html').read_bytes()).hexdigest()}
    (ROOT/'game/assets/map-presentation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':build()
