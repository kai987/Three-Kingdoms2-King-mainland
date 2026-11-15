"""Names and opening ownership previews independent of immutable save catalogs."""
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def presentation():
    path=Path(__file__).resolve().parents[2]/'game/assets/map-presentation.json'
    return json.loads(path.read_text())


def city_names(catalog,year,month=1):
    overrides=presentation()['city_names']
    names={}
    for city in catalog.data['cities']:
        row=overrides.get(city['id'],{})
        label=row.get('displayName',city['name'])
        if year<212:label=row.get('before212',label)
        if year<221:label=row.get('before221',label)
        for period in catalog.data.get('city_history',{}).get(city['id'],{}).get('names',[]):
            start=tuple(period.get('from_date',[period.get('start',1),1]))
            end=tuple(period.get('to_date',[period.get('end',9999),12]))
            if start<=(year,month)<=end:label=period['name']
        names[city['id']]=label
    return names


# Flat, saturated colors keep the native castle pixels legible. White belongs
# exclusively to neutral cities. CIELAB spacing separates factions that share
# a map, including when a custom scenario needs additional swatches.
_FACTION_SWATCHES = (
    '#f8b800', '#f85898', '#00e8d8', '#f83800', '#b8f818', '#6844fc',
    '#fc7460', '#58d854', '#3cbcfc', '#d800cc', '#503000', '#005800',
    '#0000bc', '#a40000', '#888888', '#b8b8f8', '#fca044', '#00a800',
    '#008088', '#4028a8', '#b87800', '#607c00', '#b8e8b8', '#f8d878',
    '#a868b8', '#009438', '#0078f8', '#940084', '#0078a8', '#e4c490',
)
# These scenarios use different faction IDs for the same power after succession.
_COLOR_INHERITANCE = {
    'liu_zhang': 'liu_yan',
    'sun_jian': 'wu',
    'yuan_shang': 'yuan_shao',
    'zhang_xiu': 'zhang_ji',
}

# Published faction colors are independent of the other factions in an opening.
# Keep enough perceptual separation for every pair that appears together.
_FACTION_COLORS = {
    'bao_xin': '#a868b8',
    'bian_zhang': '#a868b8',
    'cao_zhang': '#008088',
    'ding_yuan': '#009438',
    'dong_zhuo': '#a0ff80',
    'gao_gan': '#008088',
    'gongsun': '#009438',
    'gongsun_zan': '#008088',
    'han': '#f83800',
    'han_fu': '#f83800',
    'han_sui': '#b8f818',
    'han_xuan': '#a868b8',
    'hua_xin': '#a868b8',
    'jin_xuan': '#008088',
    'kong_rong': '#20c000',
    'kong_zhou': '#8040c0',
    'li_jue': '#f83800',
    'liu_biao': '#fc7460',
    'liu_dai': '#b8b8f8',
    'liu_du': '#f83800',
    'liu_yan': '#00e8d8',
    'liu_you': '#b8b8f8',
    'liu_yu': '#e4c490',
    'lu_xing': '#009438',
    'lubu': '#e4c490',
    'ma_teng': '#d800cc',
    'nanman': '#00e8d8',
    'qiao_mao': '#b87800',
    'shi_xie': '#6844fc',
    'shu': '#f8b800',
    'song_jian': '#b8e8b8',
    'tao_qian': '#607c00',
    'wang_kuang': '#ffff80',
    'wang_lang': '#a00080',
    'wei': '#0078f8',
    'wu': '#f85898',
    'wu_ju': '#b8b8f8',
    'xu_gong': '#b87800',
    'yellow_turban': '#f8b800',
    'yuan_shao': '#888888',
    'yuan_shu': '#3cbcfc',
    'yuan_tan': '#e4c490',
    'yuan_xi': '#a868b8',
    'yuan_yi': '#2060a0',
    'zang_ba': '#b87800',
    'zhang_chao': '#a02000',
    'zhang_chun': '#a868b8',
    'zhang_ji': '#00ff80',
    'zhang_lu': '#ffff80',
    'zhang_miao': '#00ff00',
    'zhang_yang': '#804040',
    'zhao_fan': '#607c00',
}
_COLOR_PRIORITY = ('wei', 'shu', 'wu', 'nanman', 'han', 'yellow_turban')


@lru_cache(maxsize=None)
def color_lab(color):
    """sRGB hex to D65 CIELAB, used only to space display swatches."""
    rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    xyz=[sum(a*b for a,b in zip(row,rgb))/white for row,white in (
        ((.4124564,.3575761,.1804375),.95047),
        ((.2126729,.7151522,.0721750),1),
        ((.0193339,.1191920,.9503041),1.08883))]
    def convert(value):
        delta=6/29
        return value**(1/3) if value>delta**3 else value/(3*delta**2)+4/29
    x,y,z=map(convert,xyz)
    return 116*y-16,500*(x-y),200*(y-z)


def color_distance(first,second):
    """CIE76 spacing; a design guard, not a color-vision accessibility claim."""
    return sum((a-b)**2 for a,b in zip(color_lab(first),color_lab(second)))**.5


@lru_cache(maxsize=1)
def _extended_faction_swatches():
    """Deterministic RGB candidates for openings beyond the native palette."""
    levels=(*range(0,256,32),255)
    return tuple(color for r in levels for g in levels for b in levels
                 if color_lab(color:='#%02x%02x%02x'%(r,g,b))[0]>=35
                 and color_distance(color,'#ffffff')>=30)


@lru_cache(maxsize=256)
def _faction_colors(identities):
    chosen={}
    reserved=['#ffffff','#000000']
    def separation(color):
        return min(color_distance(color,other) for other in [*reserved,*chosen.values()])
    preferred = sorted(identities, key=lambda identity: (identity not in _COLOR_PRIORITY, identity))
    for identity in preferred:
        color = _FACTION_COLORS.get(_COLOR_INHERITANCE.get(identity, identity))
        if color and separation(color) >= 29:
            chosen[identity] = color
    for identity in identities:
        if identity in chosen:continue
        remaining=[color for color in _FACTION_SWATCHES if color not in chosen.values()
                   and color_lab(color)[0]>=35 and color_distance(color,'#ffffff')>=30]
        best=max(remaining,key=separation,default=None)
        # Preserve native fills until their best spacing becomes insufficient.
        # Current openings have up to25 factions. Larger unknown catalogs keep
        # distinct fills, but cannot be promised the same perceptual spacing.
        if best is None or separation(best)<29:
            expanded=[color for color in _extended_faction_swatches()
                      if color not in chosen.values()]
            candidate=max(expanded,key=separation,default=None)
            if candidate is not None and (best is None or separation(candidate)>separation(best)):
                best=candidate
        if best is None:
            raise ValueError('Too many factions for the display palette')
        chosen[identity]=best
    return tuple([('neutral','#ffffff'),*sorted(chosen.items())])


def faction_colors(catalog):
    """Return an independent display palette without changing save/catalog data."""
    return dict(_faction_colors(tuple(sorted(key for key in catalog.factions if key!='neutral'))))
