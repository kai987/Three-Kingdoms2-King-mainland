#!/usr/bin/env python3
"""Complete playable v15 placement plans without rewriting released catalogs.

Same-date SAN14 guide facts, primary-text career boundaries and authored board
allocation are different evidence classes. Missing exact postings use recorded
person-specific locations and labelled continuity/region choices, never a
fabricated SAN14 export. Future entrants remain recruitable free people.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import argparse
import hashlib
import json

from build_campaigns import ROOT, read, write
from build_dlc_campaigns import finish_audits
from remake.garrison_postings import SOURCE_CITY_ALIASES
from remake.officers import PersonDefinition, YearState, year_state

FOLDER = 'main-scenarios-v15/'
SOURCE = 'https://xgodgame.blogspot.com/2020/02/14_9.html'
EXCLUDED = ('scenario_excluded', 'closed_career')


def year_status(person, year):
    return year_state(PersonDefinition(person['person_id'], person['name'], person['birth_year'],
        person['service_year'], person['death_year'], person['chronology_basis']), year)


def month_number(date):
    return date[0] * 12 + date[1] - 1


def inside(rule, date):
    return tuple(rule['from']) <= tuple(date) <= tuple(rule['to'])


class Planner:
    def __init__(self):
        self.index = read('game/data/main-scenarios-v14/index.json')
        self.parents = [read('game/data/' + path) for path in self.index['catalogs']]
        self.history = read('game/config/placement-history-v15.json')
        self.wiki = read('game/config/san14-scenario-postings-v15.json')
        self.source_hashes = {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in (
            'game/config/placement-history-v15.json', 'game/config/san14-scenario-postings-v15.json',
            'expansion/officers/data/scenario-states.json')}
        self.expansion = {r['person_id']: r for r in read('game/config/officer-expansion-v13.json')['people']}
        self.reviews = read('game/config/roster-review-v13.json')['entries']
        self.snapshots = defaultdict(list)
        for row in read('expansion/officers/data/scenario-states.json')['rows']:
            if row['historical_timeline']:
                self.snapshots[row['person_id']].append(row)
        self.peers = defaultdict(list)
        self.name_ids = defaultdict(set)
        self.ruler_sides = defaultdict(set)
        for data in self.parents:
            date = data['start_year'], data['start_month']
            for p in data['people']:
                for name in [p['name'], *p.get('aliases', [])]:
                    self.name_ids[name].add(p['person_id'])
            if not data['main_scenario'].get('fictional'):
                for pid, row in data['era_assignments'].items():
                    self.peers[pid].append((date, row, data['id'], data['appearance_locations'].get(pid)))
            for faction in data['factions']:
                self.ruler_sides[faction['captain']].add(faction['id'])
        for row in read('expansion/officers/data/roster-candidates.json')['officers']:
            for name in [row['name_japanese'], row['name_traditional'], *row.get('aliases', [])]:
                self.name_ids[name].add(row['person_id'])
        self.names = {pid: p['name'] for p in self.parents[0]['people'] for pid in [p['person_id']]}
        self.board_ids = {c['id'] for c in self.parents[0]['cities']}
        self.board_aliases = dict(SOURCE_CITY_ALIASES)
        self.board_aliases.update({c['name']: c['id'] for c in self.parents[0]['cities']})
        for row in self.history.get('career_overrides', []) + self.history.get('free_region_overrides', []):
            if row['person_id'] not in self.name_ids.get(row['name'], set()):
                raise ValueError('Historical identity mismatch: ' + row['person_id'])

    def same_name(self, a, b):
        if a == b:
            return True
        return bool(self.name_ids.get(a, set()) & self.name_ids.get(b, set()))

    def faction(self, ruler, data):
        if not ruler:
            return None
        exact = [f['id'] for f in data['factions'] if self.same_name(ruler, f['captain'])]
        if len(exact) == 1:
            return exact[0]
        options = set()
        enabled = {f['id'] for f in data['factions']}
        for name, sides in self.ruler_sides.items():
            if self.same_name(ruler, name):
                options.update(sides & enabled)
        return next(iter(options)) if len(options) == 1 else None

    def board_city(self, data, city, date):
        key = city if city in self.board_ids else self.board_aliases.get(city)
        seen = set()
        while key in data['city_foundings']:
            rule = data['city_foundings'][key]
            if tuple(date) >= (rule['year'], rule.get('month', 1)):
                break
            if key in seen:
                raise ValueError('City parent cycle')
            seen.add(key)
            key = rule['parent']
        return key if key in self.board_ids else None

    def exact(self, person, data):
        entry = self.wiki['people'].get(person['person_id'], {})
        rows = [r for r in entry.get('scenarios', []) if
            (r['year'], r['month']) == (data['start_year'], data['start_month'])]
        # A date alone cannot identify two alternative game narratives.
        if len(rows) != 1:
            return None
        return dict(rows[0], url=entry['source_url'], response_sha256=entry['response_sha256'])

    def location(self, person, data, date):
        pid = person['person_id']
        exact = self.exact(person, data)
        if exact and self.board_city(data, exact.get('city'), date):
            return self.board_city(data, exact['city'], date), dict(basis='same_date_game_location',
                source_urls=[exact['url']], reference_date=[exact['year'], exact['month']],
                reference_scenario=exact['title'])
        # Person-specific source cities are preferable to arbitrary faction seats.
        choices = []
        for row in self.snapshots[pid]:
            city = self.board_city(data, row['city_source_name'], date)
            if city:
                src_date = row['scenario_year'], row['scenario_month']
                choices.append((abs(month_number(src_date)-month_number(date)), src_date, city, row))
        if choices:
            _, src_date, city, row = min(choices, key=lambda r: (r[0], r[1], r[2]))
            return city, dict(basis='person_specific_SAN14_location_board_proxy', source_urls=[SOURCE],
                reference_date=list(src_date), reference_scenario=row['scenario_id'])
        for src_date, row, scenario, appearance in sorted(self.peers[pid],
                key=lambda r: (abs(month_number(r[0])-month_number(date)), r[0], r[2])):
            city = self.board_city(data, row.get('city') or appearance, date)
            if city:
                return city, dict(basis='retained_person_specific_released_location',
                    source_urls=self.person_sources(person), reference_date=list(src_date), reference_scenario=scenario)
        entry = self.expansion.get(pid)
        if entry:
            for window in entry['membership_windows']:
                city = self.board_city(data, window['city'], date)
                if city:
                    return city, dict(basis='primary_referenced_career_region_board_proxy',
                        source_urls=[s['url'] for s in entry['sources']], reference_date=window['from'], reference_scenario=None)
        raise ValueError('No person-specific city evidence: ' + pid)

    @staticmethod
    def person_sources(person):
        source = person.get('ability_source', {})
        return source.get('source_urls') or ([source['source_url']] if source.get('source_url') else [SOURCE])

    def review(self, basis, sources, note, **extra):
        certainty = ('game_reference' if basis.startswith('same_date') else
                     'bounded_career_inference' if 'career' in basis or 'continuity' in basis else
                     'authorial_region_placement')
        return dict(basis=basis, source_urls=list(dict.fromkeys(sources)), note=note,
            reference_date=None, reference_scenario=None, historical_certainty=certainty, **extra)

    def membership(self, person, data, prior, exact):
        pid = person['person_id'];date = data['start_year'], data['start_month']
        fictional = bool(data['main_scenario'].get('fictional'))
        enabled = {f['id'] for f in data['factions']}
        # Explicit IF participants/exclusions and ruler seats are narrative facts.
        if fictional and prior.get('faction') in enabled and prior.get('source_status') == 'serving':
            return prior['faction'], self.review('retained_explicit_IF_membership',
                data['main_scenario'].get('source_urls', []) or [data['main_scenario'].get('official_source') or SOURCE],
                '保留本篇假想局勢的明列／既有成員，非史實連續任職證明。')
        if not fictional:
            for rule in self.history.get('free_region_overrides', []):
                if rule['person_id'] == pid and inside(rule, date):
                    return None, self.review(rule['basis'], rule['source_urls'], rule['note'])
            for rule in self.history.get('career_overrides', []):
                if rule['person_id'] == pid and inside(rule, date) and rule['faction'] in enabled:
                    return rule['faction'], self.review(rule['basis'], rule['source_urls'], rule['note'])
        if exact and exact['status'] == 'serving':
            side = self.faction(exact.get('ruler'), data)
            if side:
                proof = self.review('same_date_SAN14_guide_affiliation', [exact['url']],
                    '同年月攻略逐人表所載遊戲歸屬；本作疆界與劇本仍為獨立改編，不是官方匯出或史實駐軍。')
                proof.update(reference_date=list(date), reference_scenario=exact['title'])
                return side, proof
            return None, self.review('unrepresented_source_faction_local_free_design', [exact['url']],
                '來源所屬勢力未在本篇獨立建國，保留其活動區域為可尋訪人物；不按城池顏色強迫改投。')
        if exact and exact['status'] in ('free', 'undiscovered', 'not_appeared'):
            # Birth/service gating is handled separately; available undiscovered
            # people follow this remake's existing free recruitment mechanics.
            return None, self.review('same_date_SAN14_guide_free_location', [exact['url']],
                '同年月來源為在野／未發現，達出仕年後按本作在野尋訪規則配置，不稱史實退仕。')
        if prior.get('status') == 'serving' or (prior.get('status') == 'pending_capacity' and prior.get('faction') in enabled):
            return prior['faction'], self.review('retained_reviewed_opening_membership', self.person_sources(person),
                '沿用本篇已配置歸屬；駐城在99人限制內優先來源城，其餘按邊境防務均衡安排。')
        entry = self.expansion.get(pid)
        if entry:
            current = next((w for w in entry['membership_windows'] if inside(w, date)), None)
            if current:
                return (current['faction'] if current['faction'] in enabled else None), self.review(
                    'primary_referenced_bounded_career_inference', [s['url'] for s in entry['sources']],
                    current.get('basis', '原典身分／任職窗口與本作月份估計分開；城市為地區代理。'))
        for rule in self.reviews:
            if rule['person_id'] == pid and tuple(rule['from_date']) <= date <= tuple(rule['to_date']) and rule['faction'] in enabled:
                return rule['faction'], self.review('reviewed_bounded_career_inference', rule['sources'], rule['basis'])
        if prior.get('status') == 'free':
            return None, self.review('retained_person_specific_free_location', self.person_sources(person),
                '沿用本篇已配置在野狀態及人物所在地，非新增歷史退仕判斷。')
        dated = [r for r in self.snapshots[pid] if r['status'] == 'serving']
        past_sources = sorted((r for r in dated if (r['scenario_year'], r['scenario_month']) <= date),
            key=lambda r: (r['scenario_year'], r['scenario_month']), reverse=True)
        future_sources = sorted((r for r in dated if (r['scenario_year'], r['scenario_month']) > date),
            key=lambda r: (r['scenario_year'], r['scenario_month']))
        for source in past_sources + future_sources:
            side = self.faction(source.get('ruler_source_name'), data)
            if side:
                proof = self.review('authored_bounded_source_snapshot_continuity', [SOURCE],
                    '依本人已記錄的SAN14年代所屬作本作有限延續／向前窗口配置；來源未給逐月轉屬，不能當作史實確證。')
                proof.update(reference_date=[source['scenario_year'], source['scenario_month']],
                    reference_scenario=source['scenario_id'])
                return side, proof
        # All gaps are given a playable disposition. Continuity is an explicit
        # authorial inference from individual dated records, not invented fact.
        rows = [(d, r, s) for d, r, s, _ in self.peers[pid] if r.get('status') == 'serving']
        past = sorted((r for r in rows if r[0] <= date), key=lambda r: r[0], reverse=True)
        future = sorted((r for r in rows if r[0] > date), key=lambda r: r[0])
        for src_date, row, scenario in past + future:
            side = row.get('faction')
            if side in enabled:
                proof = self.review('authored_bounded_snapshot_continuity', self.person_sources(person),
                    '依此人最近可用年代的在籍記錄作本作連續任職／提前窗口推定；非逐月史實已證。')
                proof.update(reference_date=list(src_date), reference_scenario=scenario)
                return side, proof
        return None, self.review('authorial_region_placement', self.person_sources(person),
            '本年月缺乏可用所屬勢力證據，依此人既有來源活動區域配置為在野待訪；不冒充史實辭官或投靠。')

    def future_windows(self, person, data):
        pid = person['person_id'];date = data['start_year'], data['start_month']
        start = max(date, (person['service_year'], 1))
        end = person['death_year'], 12
        if start > end:
            return [], None
        entry = self.expansion.get(pid)
        candidates = []
        if entry:
            for rule in entry['membership_windows']:
                a = max(start, tuple(rule['from']));b = min(end, tuple(rule['to']))
                if a <= b:
                    city = self.board_city(data, rule['city'], a)
                    candidates.append((a, b, city))
        else:
            city, _ = self.location(person, data, start)
            candidates.append((start, end, city))
        windows = [dict(start=list(a), end=list(b), city=city,
            resolve_death_year=True) for a, b, city in candidates if city]
        return windows, candidates[0][2] if candidates else None

    def build_catalog(self, previous):
        data = deepcopy(previous)
        data.update(id=previous['id'].replace('-v14', '-v15'), content_generation=15)
        data['rules']['city_officer_capacity'] = 99
        date = data['start_year'], data['start_month'];fictional = bool(data['main_scenario'].get('fictional'))
        enabled = {f['id']: f for f in data['factions']}
        corrected = []
        if not fictional:
            for rule in self.history.get('city_owner_corrections', []):
                if not inside(rule, date):
                    continue
                for city in rule['cities']:
                    if data['initial_owners'].get(city) == rule['only_when_owner']:
                        data['initial_owners'][city] = rule['faction']
                        data['city_history'].setdefault(city, {})['placement_owner_review'] = deepcopy(rule)
                        corrected.append(city)
        old_rows = {r['person_id']: r for r in previous['initial_officers']}
        rulers = {pid: side for side, ident in data['faction_rulers'].items()
                  for pid in [next(p['person_id'] for p in data['people'] if p['runtime_id'] == ident)]}
        initial, free, assignments, locations, windows = [], [], {}, {}, {}
        for person in data['people']:
            pid = person['person_id'];ys = year_status(person, date[0]);prior = deepcopy(previous['era_assignments'][pid])
            exact = self.exact(person, data)
            excluded = prior.get('status') in EXCLUDED
            snapshot_dead = any((r['scenario_year'], r['scenario_month']) == date and r['status'] == 'dead'
                for r in self.snapshots[pid])
            source_dead = bool(not fictional and ((exact and exact['status'] == 'dead') or snapshot_dead) and pid not in rulers)
            if excluded or source_dead or ys == YearState.DEAD:
                proof = self.review('same_date_SAN14_recorded_death' if source_dead else 'retained_chronology_or_explicit_exclusion',
                    [exact['url'] if exact and exact['status'] == 'dead' else SOURCE] if source_dead else self.person_sources(person),
                    '本篇來源記已死亡或明列故事排除，不生成、不復活。' if source_dead or excluded else '本作年表已過退場／卒年，不配置在籍或未來登場。')
                prior.update(status='scenario_excluded' if source_dead or excluded else 'chronology_excluded',
                    faction=None, city=None, year_state=ys.value, planning_complete=True, placement_review=proof,
                    appearance_plan=dict(start=None, end=None, city=None, status='excluded', basis=proof['basis']))
                if source_dead:prior['exclusion_kind'] = 'same_date_reference_dead'
                windows[pid] = [];assignments[pid] = prior
                continue
            if ys in (YearState.NOT_BORN, YearState.NOT_APPEARED):
                planned, city = self.future_windows(person, data)
                if not planned:
                    raise ValueError('Future person lacks appearance window: ' + pid)
                _, loc_proof = self.location(person, data, tuple(planned[0]['start']))
                proof = self.review('person_specific_future_free_appearance', loc_proof['source_urls'],
                    '先按出生、出仕與生涯窗口判斷；到達首個窗口才以在野出場，沒有強制歷史入仕或改投。')
                prior.update(status='chronology_excluded', faction=None, city=city, year_state=ys.value,
                    planning_complete=True, placement_review=proof, appearance_plan=dict(start=planned[0]['start'],
                    end=planned[-1]['end'], city=city, status='future_free', basis=loc_proof['basis']))
                windows[pid] = planned;locations[pid] = city;assignments[pid] = prior
                continue
            if ys not in (YearState.AVAILABLE, YearState.DEATH_YEAR_REVIEW):
                raise ValueError('Unresolved chronology: ' + pid)
            side, proof = self.membership(person, data, prior, exact)
            if pid in rulers:
                side = rulers[pid]
                proof = self.review('retained_explicit_scenario_ruler', self.person_sources(person),
                    '保留本篇明列君主及根據地，不以外部快照覆寫劇本君主。')
            city, loc_proof = self.location(person, data, date)
            if not fictional:
                region = next((r for r in self.history.get('free_region_overrides', []) if r['person_id'] == pid and inside(r, date)), None)
                if region:city = self.board_city(data, region['city'], date)
            old_posting = prior.get('posting_reference') or {}
            preserved_posting = (deepcopy(old_posting) if
                old_posting.get('basis') == 'attested_yanmen_post_227' and
                side is not None and old_posting.get('faction') == side else None)
            prior.update(status='serving' if side else 'free', source_status='serving' if side else 'free',
                faction=side, city=enabled[side]['city'] if side else city, year_state=ys.value,
                reason=None, death_year_resolved=ys == YearState.DEATH_YEAR_REVIEW,
                planning_complete=True, placement_review=proof, posting_reference=preserved_posting)
            primary_post = next((r for r in self.history.get('career_overrides', []) if
                not fictional and r['person_id'] == pid and inside(r, date) and
                r['faction'] == side and r.get('city')), None)
            if primary_post:
                prior['historical_posting_reference'] = dict(
                    basis='primary_referenced_career_posting',
                    city=self.board_city(data, primary_post['city'], date),
                    source_urls=primary_post['source_urls'], note=primary_post['note'])
            if side:
                row = deepcopy(old_rows.get(pid, dict(person_id=pid, troops=300)))
                row.update(city=enabled[side]['city'], ruler=pid in rulers,
                    resolve_death_year=ys == YearState.DEATH_YEAR_REVIEW)
                initial.append(row)
                if exact and exact['city']:
                    prior['source_city'] = exact['city']
                    prior['source_city_reference'] = dict(url=exact['url'], source_scenario_date=list(date),
                        title=exact['title'], basis='same_date_SAN14_guide_city_not_official_export')
            else:
                free.append(dict(person_id=pid, city=city, resolve_death_year=ys == YearState.DEATH_YEAR_REVIEW))
                prior['source_city'] = exact['city'] if exact and exact['city'] else prior.get('source_city')
            prior['appearance_plan'] = dict(start=list(date), end=[person['death_year'], 12],
                city=prior['city'], status=prior['status'], basis=loc_proof['basis'])
            assignments[pid] = prior;locations[pid] = prior['city'];windows[pid] = []
        data.update(initial_officers=initial, initial_free_officers=free,
            era_assignments=assignments, appearance_locations=locations, appearance_windows=windows)
        finish_audits(data)
        for row in initial:
            assignments[row['person_id']]['appearance_plan']['city'] = row['city']
        data['coverage'].update(pending_history=0, pending_faction=0, pending_capacity=0,
            pending_factions=[], placement_plans=len(assignments), future_plans=sum(bool(w) for w in windows.values()))
        data['placement_completion'] = dict(schema='tk2-placement-completion-v15', complete=True, pending=0,
            people=len(assignments), capacity=99, future_plans=data['coverage']['future_plans'],
            reference_classes=dict(Counter(a['placement_review']['historical_certainty'] for a in assignments.values())),
            bases=dict(Counter(a['placement_review']['basis'] for a in assignments.values())),
            city_owner_corrections=corrected, source_snapshot_complete=self.wiki.get('snapshot_complete', False),
            source_hashes=self.source_hashes,
            source_coverage=dict(dated_snapshot_people=len(self.snapshots),
                newly_checked_guide_people=len(self.wiki['people'])),
            source_boundary='Configuration complete; exact historical postings are not all established. Authorial continuity/regions are labelled per person.',
            parent_catalog=previous['id'])
        data['main_scenario'].update(roster_complete=True,
            roster_completeness_scope='all1023 opening/excluded/future plans, not attested complete historical garrisons')
        data['design_notes'] = [n for n in previous['design_notes'] if not any(t in n for t in
            ('30人', '待配置', '待考', '未確認', '未确认', '每城', 'Each city'))] + [
            '每城最多99人；每方出戰最多10人。人物總庫1023人，各年代按出生、出仕、死亡及明列劇本分歧配置。',
            '全部人物均完成在籍、在野、未來登場或明列排除計畫；來源不詳的駐城與連續任職屬本作配置，不是逐月史實已證。',
            '優先同年月SAN14攻略表及原典生涯窗口；其餘依本人既有年代／區域記錄推定，駐軍再按來源城及邊境容量均衡分配。',
            '未來人物到達出仕窗口才以在野待訪，不強迫在遊玩中改投歷史勢力；已登場身分不重複生成、不復活。',
            '新規則用於v15新開戰役；既有v14及更早存檔繼續沿用其原目錄與容量，不改寫玩家進度。']
        data['era_metadata']['main_scenario'] = deepcopy(data['main_scenario'])
        return data


def build(check=False):
    planner = Planner();catalogs, summary = [], []
    for path, previous in zip(planner.index['catalogs'], planner.parents):
        data = planner.build_catalog(previous)
        name = FOLDER + path.rsplit('/', 1)[-1]
        raw = (json.dumps(data, ensure_ascii=False, separators=(',', ':'))+'\n').encode()
        if check:
            if (ROOT/'game/data'/name).read_bytes() != raw:
                raise ValueError('Placement catalog differs: ' + name)
        else:write('game/data/' + name, data)
        catalogs.append(name)
        summary.append(dict(id=data['id'], year=data['start_year'], month=data['start_month'],
            library=len(data['people']), serving=len(data['initial_officers']), free=len(data['initial_free_officers']),
            future=data['coverage']['future_plans'], pending=0, capacity=99,
            reference_classes=data['placement_completion']['reference_classes']))
    result = dict(schema='main-scenario-index-v1', catalogs=catalogs, default='mainland217-07-v15', summary=summary)
    if check:
        if read('game/data/'+FOLDER+'index.json') != result:
            raise ValueError('Placement index differs')
    else:write('game/data/'+FOLDER+'index.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build(args.check)
    print(json.dumps(dict(catalogs=len(result['catalogs']), capacity=99,
        people_per_catalog=1023, total_plans=sum(r['library'] for r in result['summary']),
        pending=sum(r['pending'] for r in result['summary']), check=args.check)))
