"""Apply reviewed historical and Romance of the Three Kingdoms XIV opening posts."""

from collections import Counter


# Officer scenario tables linked from https://wikiwiki.jp/sangokushi14/200年1月　官渡の戦い
GUANDU_MA_TENG_POSTS = {
    'san14-candidate-0760': 'wuwei',     # Ma Xiu
    'san14-candidate-0770': 'wuwei',     # Ma Tie
    'san14-candidate-0804': 'wuwei',     # Fu Gan
    'san14-candidate-0757': 'anding',   # Ma Yunlu
    'san14-candidate-0766': 'anding',   # Ma Dai
    'san14-candidate-0769': 'anding',   # Ma Chao
    'san14-candidate-0830': 'anding',   # Pang De
    'san14-candidate-0969': 'tianshui',  # Liang Xing
}

# Original scenario rows for these officers list them in Wuwei.
# https://wikiwiki.jp/sangokushi14/傅幹
# https://wikiwiki.jp/sangokushi14/馬超
# https://wikiwiki.jp/sangokushi14/ホウ徳
# https://wikiwiki.jp/sangokushi14/馬休
# https://wikiwiki.jp/sangokushi14/馬鉄
FU_GAN = 'san14-candidate-0804'
MA_CHAO = 'san14-candidate-0769'
PANG_DE = 'san14-candidate-0830'
MA_XIU_AND_MA_TIE = ('san14-candidate-0760', 'san14-candidate-0770')
EARLY_WUWEI = (FU_GAN, MA_CHAO, PANG_DE)
LATER_WUWEI = (FU_GAN, *MA_XIU_AND_MA_TIE)
WUWEI_COMPANIONS = {
    'mainland194-06': (*EARLY_WUWEI, *MA_XIU_AND_MA_TIE),
    'mainland196-06': (*EARLY_WUWEI, *MA_XIU_AND_MA_TIE),
    'mainland197-07': (*EARLY_WUWEI, *MA_XIU_AND_MA_TIE),
    'mainland198-03': LATER_WUWEI,
    'mainland201-05': (FU_GAN,),
    'mainland202-06': LATER_WUWEI,
    'mainland207-09': LATER_WUWEI,
    'mainland208-10': (FU_GAN,),
    'mainland209-06': MA_XIU_AND_MA_TIE,
    'mainland210-11': LATER_WUWEI,
    # Our Tong Pass opening uses Wuwei as Ma Chao's seat. Pang De follows his
    # lord as in the reference's Chang'an deployment.
    'mainland211-07-tongguan': (PANG_DE,),
}

# Wei You was Liu Yu's East Bureau officer. Post him with his governor
# at Ji, following the recorded relationship without assuming a precise date.
# https://zh.wikisource.org/wiki/後漢書/卷73
WEI_YOU = 'san14-candidate-0196'
GAO_ROU = 'san14-candidate-0253'
OPENING_POSTS = {
    **{scenario: dict.fromkeys(people, 'wuwei') for scenario, people in WUWEI_COMPANIONS.items()},
    'mainland190-01': {**dict.fromkeys(EARLY_WUWEI, 'wuwei'), WEI_YOU: 'yan'},
    'mainland191-10': {**dict.fromkeys(EARLY_WUWEI, 'wuwei'), WEI_YOU: 'yan'},
    'mainland200-01': GUANDU_MA_TENG_POSTS,
    # The original places Gao Rou under Gao Gan at Jinyang.
    # https://wikiwiki.jp/sangokushi14/高柔
    'mainland202-06': {**dict.fromkeys(LATER_WUWEI, 'wuwei'), GAO_ROU: 'taiyuan'},
    # Cao Zhang and Qian Zhao are stationed together in the fictional original
    # scenario. Our version uses Taiyuan for Cao Zhang's headquarters.
    # https://wikiwiki.jp/sangokushi14/牽招
    'mainland212-06': {'san14-candidate-0236': 'taiyuan'},
}


def apply(data):
    """Revise new openings while keeping saved campaigns tied to the same catalog."""
    posts = OPENING_POSTS.get(data['id'])
    if posts is None or data['officer_count'] < 1083:
        return

    officers = {row['person_id']: row for row in data['initial_officers']}
    owners = data['initial_owners']
    governors = data.get('initial_governors', {})
    for person, city in posts.items():
        officer = officers[person]
        source = officer['city']
        old_owner, new_owner = owners[source], owners[city]
        recorded_transfer = (data['id'], person, old_owner, new_owner) == (
            'mainland202-06', GAO_ROU, 'yuan_shang', 'gao_gan')
        if (officer['ruler'] or new_owner == 'neutral'
                or (old_owner != new_owner and not recorded_transfer)
                or (source != city and governors.get(source, {}).get('person_id') == person)):
            raise ValueError(f'{data["id"]}: invalid opening post for {person} at {city}')
        officer['city'] = city
        data['appearance_locations'][person] = city
        era = data['era_assignments'][person]
        era['city'] = city
        era['appearance_plan']['city'] = city
        era['posting_reference']['city'] = city
        if recorded_transfer:
            era['faction'] = era['posting_reference']['faction'] = new_owner
            for faction in data['factions']:
                if faction['id'] == old_owner:
                    faction['initial_officers'] -= 1
                elif faction['id'] == new_owner:
                    faction['initial_officers'] += 1

    if data['id'] == 'mainland200-01':
        governors['anding'] = {
            'person_id': MA_CHAO,
            'source': 'https://wikiwiki.jp/sangokushi14/馬超',
        }
    roster_sizes = Counter(row['city'] for row in officers.values())
    data['coverage']['planned_max_city_roster'] = max(roster_sizes.values())
