"""Luoyang and Chang'an after the 190 court relocation."""

MOVED_PERCENT = 72
LOST_PERCENT = 25
UNIT = 100
LUOYANG_OPENING_POPULATION = 203_100


def relocation_amounts(stock, room):
    moved = min(stock * MOVED_PERCENT // 100, room) // UNIT * UNIT
    lost = stock * LOST_PERCENT // (100 * UNIT) * UNIT
    return moved, lost


_MOVED_POPULATION, _DISPERSED_POPULATION = relocation_amounts(
    LUOYANG_OPENING_POPULATION, LUOYANG_OPENING_POPULATION)
_FIELDS = ('population', 'gold', 'grain', 'troop_percent', 'land', 'industry',
           'governance', 'preparedness', 'town', 'damage')

# Game estimates anchored to the relocation and fire, the post-192 struggle
# and 195 famine in Chang'an, and the later restoration of Luoyang under Wei.
# Stocks fall between the move and the later openings as resources are used.
_OPENINGS = {
    'henan': (
        ((190, 2), (LUOYANG_OPENING_POPULATION - _MOVED_POPULATION - _DISPERSED_POPULATION,
                    170, 325, 100,  95,  67, 26, 14, 1, 50)),
        ((191,10), (  6_900,   500,  1_100, 100, 112,  84, 32, 18, 1, 42)),
        ((196, 6), ( 15_700,   800,  1_850,  45, 139, 100, 44, 24, 1, 31)),
        ((200, 1), ( 25_900, 1_900,  6_100,  75, 215, 171, 55, 31, 1, 20)),
        ((207, 9), ( 47_500, 2_600,  8_100,  90, 275, 225, 63, 37, 2, 12)),
        ((219, 7), ( 83_500, 3_400, 10_000, 100, 321, 263, 71, 44, 2,  5)),
        ((221, 7), ( 94_100, 6_100, 18_000, 115, 400, 358, 81, 53, 3,  2)),
        ((225, 7), (127_900, 6_200, 18_100, 114, 410, 374, 82, 55, 3,  1)),
        ((227, 2), (137_400, 6_250, 18_200, 114, 414, 380, 83, 56, 3,  1)),
        ((234, 2), (155_000, 6_500, 18_500, 113, 419, 390, 85, 59, 3,  0)),
        ((238, 1), (164_900, 6_650, 18_800, 112, 429, 399, 86, 61, 3,  0)),
        ((249, 1), (181_300, 7_000, 20_000, 110, 441, 415, 87, 63, 3,  0)),
        ((263, 5), (198_200, 6_650, 19_600, 108, 437, 402, 85, 61, 3,  0)),
    ),
    'jingzhao': (
        ((190, 2), (98_100 + _MOVED_POPULATION,
                   55_190,114_725, 100, 258, 222, 71, 40, 2,  0)),
        ((191,10), (207_500,24_500, 43_000, 100, 285, 260, 66, 44, 3,  3)),
        ((194, 6), (148_800, 6_400, 10_700, 135, 209, 185, 47, 28, 2, 19)),
        ((196, 6), ( 86_000, 1_150,  2_650,  83, 154, 120, 37, 21, 1, 30)),
        ((200, 1), ( 83_500, 1_650,  4_250, 100, 193, 148, 52, 30, 2, 17)),
        ((207, 9), ( 94_000, 2_450,  6_500, 106, 231, 177, 64, 35, 2,  8)),
        ((211, 7), (102_600, 2_900,  8_200, 125, 244, 193, 66, 41, 2,  9)),
        ((221, 7), (108_600, 2_700,  7_600, 109, 268, 223, 75, 48, 2,  3)),
        ((234, 2), (124_400, 3_750, 10_800, 117, 299, 256, 79, 54, 2,  0)),
        ((249, 1), (129_600, 3_680, 10_900, 110, 308, 268, 80, 56, 2,  0)),
        ((263, 5), (122_000, 3_450,  9_800, 106, 300, 255, 78, 53, 2,  0)),
    ),
}
_QUANTA = {'population': UNIT, 'gold': 10, 'grain': 25}
# The first post-relocation scenario still reflects the depletion and arrival
# of city reserves. Later scenarios use their own dated reserve stocks.
_RESERVES_AFTER_RELOCATION = {'henan': 300, 'jingzhao': 1_800}


def opening(data, city):
    """Return the capital's reviewed opening figures for this calendar date."""
    if city not in _OPENINGS or not data.get('id', '').startswith('mainland'):
        return {}
    date = data['start_year'], data['start_month']
    anchors = _OPENINGS[city]
    if not anchors[0][0] <= date <= anchors[-1][0]:
        return {}
    for (start, base), (end, later) in zip(anchors, anchors[1:]):
        if date == end:
            row = dict(zip(_FIELDS, later))
            if date == (191, 10):
                row['reserves'] = _RESERVES_AFTER_RELOCATION[city]
            return row
        if date < end:
            months = (end[0] - start[0]) * 12 + end[1] - start[1]
            elapsed = (date[0] - start[0]) * 12 + date[1] - start[1]
            row = {}
            for field, before, after in zip(_FIELDS, base, later):
                quantum = _QUANTA.get(field, 1)
                amount = (before * (months - elapsed) + after * elapsed) // months
                row[field] = before if field == 'town' else amount // quantum * quantum
            return row
