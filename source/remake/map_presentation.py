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
        names[city['id']]=row.get('before212',label) if year<212 else label
    return names
