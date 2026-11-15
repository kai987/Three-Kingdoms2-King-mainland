"""Names and opening ownership previews independent of immutable save catalogs."""
from functools import lru_cache
import json
from math import dist
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
# exclusively to neutral cities. Oklab spacing separates factions that share
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
    'bao_xin': '#406080',
    'bian_zhang': '#a868b8',
    'cao_zhang': '#008088',
    'ding_yuan': '#009438',
    'dong_zhuo': '#00c0ff',
    'gao_gan': '#008088',
    'gongsun': '#c0c0ff',
    'gongsun_zan': '#a00000',
    'han': '#f83800',
    'han_fu': '#a06000',
    'han_sui': '#a020ff',
    'han_xuan': '#a868b8',
    'hua_xin': '#4080a0',
    'jin_xuan': '#008088',
    'kong_rong': '#009000',
    'kong_zhou': '#a060a0',
    'li_jue': '#f83800',
    'liu_biao': '#c0ffa0',
    'liu_dai': '#406000',
    'liu_du': '#f83800',
    'liu_yan': '#00e8d8',
    'liu_you': '#2000ff',
    'liu_yu': '#a0a060',
    'lu_xing': '#009438',
    'lubu': '#00b0ff',
    'ma_teng': '#d800cc',
    'nanman': '#00e8d8',
    'qiao_mao': '#20c040',
    'shi_xie': '#a00080',
    'shu': '#f8b800',
    'song_jian': '#ffa0a0',
    'tao_qian': '#00a0a0',
    'wang_kuang': '#ff7000',
    'wang_lang': '#a060a0',
    'wei': '#0078f8',
    'wu': '#f85898',
    'wu_ju': '#00c0ff',
    'xu_gong': '#b87800',
    'yellow_turban': '#f8b800',
    'yuan_shao': '#ff80ff',
    'yuan_shu': '#a080ff',
    'yuan_tan': '#a0a080',
    'yuan_xi': '#a868b8',
    'yuan_yi': '#3000ff',
    'zang_ba': '#b87800',
    'zhang_chao': '#e02020',
    'zhang_chun': '#a868b8',
    'zhang_ji': '#206000',
    'zhang_lu': '#40c000',
    'zhang_miao': '#00ff00',
    'zhang_yang': '#6040c0',
    'zhao_fan': '#607c00',
}
_COLOR_PRIORITY = ('wei', 'shu', 'wu', 'nanman', 'han', 'yellow_turban')
_MIN_FACTION_COLOR_DISTANCE = .14


@lru_cache(maxsize=None)
def color_oklab(color):
    """Convert an sRGB hex swatch to Oklab with its D65 white point."""
    # Linear sRGB conversion from https://bottosson.github.io/posts/oklab/#implementation
    rgb = (int(color[i:i+2], 16) / 255 for i in (1, 3, 5))
    r, g, b = (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb)
    l = (.4122214708*r + .5363325363*g + .0514459929*b) ** (1/3)
    m = (.2119034982*r + .6806995451*g + .1073969566*b) ** (1/3)
    s = (.0883024619*r + .2817188376*g + .6299787005*b) ** (1/3)
    return (.2104542553*l + .7936177850*m - .0040720468*s,
            1.9779984951*l - 2.4285922050*m + .4505937099*s,
            .0259040371*l + .7827717662*m - .8086757660*s)


def color_distance(first,second):
    """Return the perceptual distance between two swatches in Oklab."""
    return dist(color_oklab(first), color_oklab(second))


def _visible_faction_swatch(color):
    # The dark sprite outline and the neutral white fills stay fixed.
    return color_oklab(color)[0] >= .43 and color_distance(color, '#ffffff') >= .15


@lru_cache(maxsize=1)
def _extended_faction_swatches():
    """Deterministic RGB candidates for openings beyond the native palette."""
    levels=(*range(0,256,32),255)
    return tuple(color for r in levels for g in levels for b in levels
                 if _visible_faction_swatch(color:='#%02x%02x%02x'%(r,g,b)))


@lru_cache(maxsize=256)
def _faction_colors(identities):
    chosen={}
    reserved=['#ffffff','#000000']
    def separation(color):
        return min(color_distance(color,other) for other in [*reserved,*chosen.values()])
    preferred = sorted(identities, key=lambda identity: (identity not in _COLOR_PRIORITY, identity))
    for identity in preferred:
        color = _FACTION_COLORS.get(_COLOR_INHERITANCE.get(identity, identity))
        if color and _visible_faction_swatch(color) and separation(color) >= _MIN_FACTION_COLOR_DISTANCE:
            chosen[identity] = color
    for identity in identities:
        if identity in chosen:continue
        remaining=[color for color in _FACTION_SWATCHES if color not in chosen.values()
                   and _visible_faction_swatch(color)]
        best=max(remaining,key=separation,default=None)
        # Preserve native fills until their best spacing becomes insufficient.
        # Larger custom catalogs use the best remaining spacing in the gamut.
        if best is None or separation(best) < _MIN_FACTION_COLOR_DISTANCE:
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
