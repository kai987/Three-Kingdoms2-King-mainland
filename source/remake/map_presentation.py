"""Names and opening ownership previews independent of immutable save catalogs."""
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=1)
def presentation():
    path=Path(__file__).resolve().parents[2]/'game/assets/map-presentation.json'
    return json.loads(path.read_text())


def city_names(catalog,year):
    overrides=presentation()['city_names']
    names={}
    for city in catalog.data['cities']:
        row=overrides.get(city['id'],{})
        label=row.get('displayName',city['name'])
        if year<212:label=row.get('before212',label)
        if year<221:label=row.get('before221',label)
        for period in catalog.data.get('city_history',{}).get(city['id'],{}).get('names',[]):
            if period['start']<=year<=period['end']:label=period['name']
        names[city['id']]=label
    return names


# Flat, saturated colors keep the native castle pixels legible. White belongs
# exclusively to neutral cities; do not reuse the old near-white Wei fill.
# The allocator compares colors in CIELAB instead of accepting duplicate hues
# or relying on raw RGB distance. The full scenario faction list is the key,
# so elimination, selection, language switches and reloads never recolor it.
_FACTION_SWATCHES = (
    '#f8b800', '#f85898', '#00e8d8', '#f83800', '#b8f818', '#6844fc',
    '#fc7460', '#58d854', '#3cbcfc', '#d800cc', '#503000', '#005800',
    '#0000bc', '#a40000', '#888888', '#b8b8f8', '#fca044', '#00a800',
    '#008088', '#4028a8', '#b87800', '#607c00', '#b8e8b8', '#f8d878',
    '#a868b8', '#009438', '#0078f8', '#940084', '#0078a8', '#e4c490',
)
_FACTION_ANCHORS = (
    ('wei', '#0078f8'), ('shu', '#f8b800'), ('wu', '#f85898'),
    ('nanman', '#00e8d8'), ('han', '#f83800'),
    ('yellow_turban', '#f8b800'), ('sun_jian', '#f85898'),
)


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


@lru_cache(maxsize=256)
def _faction_colors(identities):
    chosen={}
    reserved=['#ffffff','#000000']
    def separation(color):
        return min(color_distance(color,other) for other in [*reserved,*chosen.values()])
    for identity,color in _FACTION_ANCHORS:
        if identity in identities and color not in chosen.values() and separation(color)>=30:
            chosen[identity]=color
    for identity in identities:
        if identity in chosen:continue
        remaining=[color for color in _FACTION_SWATCHES if color not in chosen.values()
                   and color_lab(color)[0]>=35 and color_distance(color,'#ffffff')>=30]
        # All released catalogs fit the native pool (at most 19 factions).
        # An unknown future catalog may use more: retain deterministic distinct
        # fills rather than recycling a previous faction's color.
        if not remaining:
            remaining=['#%02x%02x%02x'%(r,g,b)
                for r in (24,72,120,168,216) for g in (24,72,120,168,216)
                for b in (24,72,120,168,216) if '#%02x%02x%02x'%(r,g,b) not in chosen.values()
                and color_lab('#%02x%02x%02x'%(r,g,b))[0]>=35
                and color_distance('#%02x%02x%02x'%(r,g,b),'#ffffff')>=30]
        chosen[identity]=max(remaining,key=separation)
    return tuple([('neutral','#ffffff'),*sorted(chosen.items())])


def faction_colors(catalog):
    """Return an independent display palette without changing save/catalog data."""
    return dict(_faction_colors(tuple(sorted(key for key in catalog.factions if key!='neutral'))))
