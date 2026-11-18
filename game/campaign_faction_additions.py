"""Apply separately sourced historical faction openings to the shared scenario board."""

import json
from remake.southern_mission import DEPARTURE_YEAR, RETURN_YEAR


SCHEMA = 'tk2-historical-faction-openings-v1'
BASIS = 'reviewed_historical_faction_opening'


def read_faction_additions(directory, scenarios):
    records = []
    cities = set()
    for path in sorted(directory.glob('*.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        faction = row['faction']
        periods = row['periods']
        starts = [period['start'] for period in periods]
        if (row['schema'] != SCHEMA or faction['id'] != path.stem or faction['city'] in cities
                or not starts or any(a >= b for a, b in zip(starts, starts[1:]))
                or set(row.get('allies_by_scenario', {})) - scenarios):
            raise ValueError(f'Invalid historical faction source: {path.name}')
        if any((period['owner'] == faction['id']) != bool(period.get('ruler'))
               for period in periods):
            raise ValueError(f'Invalid historical faction rulers: {path.name}')
        records.append(row)
        cities.add(faction['city'])
    return records


def prepare_factions(data, opening, additions, people):
    """Register current rulers before the existing expansion owner checks."""
    date = [data['start_year'], data['start_month']]
    present = []
    existing = {row['id'] for row in data['factions']}
    for record in additions:
        faction = record['faction']
        owner_id, city = faction['id'], faction['city']
        period = next((row for row in reversed(record['periods']) if row['start'] <= date), None)
        if not period or owner_id in existing or city in opening['owners']:
            raise ValueError(f'{data["id"]}: invalid historical faction opening for {owner_id}')
        opening['owners'][city] = period['owner']
        opening['garrisons'][city] = []
        opening.setdefault('opening_notes', {})[city] = period['note']
        if 'resources' in period:
            opening.setdefault('resources', {})[city] = dict(period['resources'])
        if ruler := period.get('ruler'):
            data['factions'].append(dict(faction, captain=people[ruler]['name'], initial_officers=0))
            data['faction_rulers'][owner_id] = people[ruler]['runtime_id']
            existing.add(owner_id)
            present.append((record, period))
        elif record.get('allies_by_scenario', {}).get(data['id']):
            raise ValueError(f'{data["id"]}: an inactive historical faction cannot ally')
        if chronology := record.get('ruler_chronology'):
            apply_ruler_chronology(data, owner_id, city, chronology, record['history']['sources'], people, date)
        if officers := record.get('officer_chronology'):
            apply_officer_chronology(data, owner_id, city, officers, people, date,
                                     active=period['owner'] == owner_id)
    for record, _ in present:
        owner = record['faction']['id']
        allies = record.get('allies_by_scenario', {}).get(data['id'], [])
        if owner in allies or len(set(allies)) != len(allies) or set(allies) - existing:
            raise ValueError(f'{data["id"]}: invalid historical alliance for {owner}')
        for ally in allies:
            data.setdefault('initial_alliances', []).append({'factions': [owner, ally], 'duration': 36})
    return present


def opening_era(data, person, owner, city, sources, note, status, start, end, resolve):
    date = [data['start_year'], data['start_month']]
    certainty = ('fictional_scenario_adaptation' if data['main_scenario']['group'] == 'if'
                 else 'historical_career_with_opening_station_inference')
    pid = person['person_id']
    year_state = {'serving': 'available', 'future': 'not_appeared', 'dead': 'dead',
                  'scenario_excluded': 'available'}[status]
    if date[0] < person['birth_year']:
        year_state = 'not_born'
    return dict(source_status='historical_named_supplement', source_ruler=None, source_city=None,
                status=status, year_state=year_state,
                faction=owner if status == 'serving' else None, city=city, reason=note,
                death_year_resolved=resolve, planning_complete=True, placement_basis=BASIS,
                scenario_membership_basis=BASIS,
                posting_reference=dict(person_id=pid, faction=owner, city=city,
                                       basis=BASIS, source_urls=sources, historical_certainty=certainty),
                placement_review=dict(basis=BASIS, source_urls=sources, note=note,
                                      reference_date=date, reference_scenario=data['id'], historical_certainty=certainty),
                appearance_plan=dict(start=start, end=end, city=city,
                                     status='future_free' if status == 'future' else status, basis=BASIS))


def apply_ruler_chronology(data, owner, city, timeline, sources, people, date):
    for index, entry in enumerate(timeline):
        pid, start, exit_date = entry['person_id'], entry['start'], entry['exit']
        person = people[pid]
        if pid in data['era_assignments'] or person['service_year'] != start[0] or person['death_year'] != exit_date[0]:
            raise ValueError(f'{data["id"]}: inconsistent historical ruler chronology: {pid}')
        data['appearance_locations'][pid] = city
        data['appearance_windows'][pid] = []
        if date < start:
            data['appearance_windows'][pid].append(dict(start=start, end=exit_date, city=city, resolve_death_year=True))
        if date <= exit_date:
            data.setdefault('historical_exit_dates', {})[pid] = exit_date
        if index + 1 < len(timeline):
            successor = timeline[index + 1]
            if successor['start'] != exit_date:
                raise ValueError(f'{data["id"]}: historical successor is unavailable at {exit_date}')
            data.setdefault('historical_successions', {})[pid] = dict(
                faction=owner, nominee=successor['person_id'], admission=successor['start'])
        note = person['chronology_design']['basis']
        status = 'future' if date < start else 'dead'
        data['era_assignments'][pid] = opening_era(data, person, owner, city, sources, note,
                                                   status, start, exit_date, False)


def apply_officer_chronology(data, owner, city, officers, people, date, *, active, join_faction=False):
    """Keep each named retainer in their own documented or estimated service window."""
    for entry in officers:
        pid, start, end = entry['person_id'], entry['start'], entry['end']
        person = people[pid]
        exit_date = entry.get('exit')
        if (pid in data['era_assignments'] or start > end or person['service_year'] != start[0]
                or person['death_year'] != (exit_date or end)[0] or (exit_date and end >= exit_date)):
            raise ValueError(f'{data["id"]}: inconsistent historical officer chronology: {pid}')
        status = ('dead' if date > end else 'scenario_excluded' if not active
                  else 'future' if date < start else 'serving')
        data['appearance_locations'][pid] = city
        data['appearance_windows'][pid] = (
            [dict(start=start, end=end, city=city, resolve_death_year=True)] if status == 'future' else [])
        if active and exit_date and date <= exit_date:
            data.setdefault('historical_exit_dates', {})[pid] = exit_date
        data['era_assignments'][pid] = opening_era(data, person, owner, city, entry['sources'], entry['note'],
                                                   status, start, end, status == 'serving' and date[0] == person['death_year'])
        if join_faction and status == 'future':
            data['appearance_windows'][pid][0]['faction'] = owner
            data['era_assignments'][pid]['appearance_plan'].update(status='future', faction=owner)


def place_southern_envoys(data, opening, people):
    """Keep the named envoys off the city roster until their return."""
    owner, city = opening['faction'], opening['city']
    date = [data['start_year'], data['start_month']]
    apply_officer_chronology(data, owner, city, opening['people'], people, date,
                             active=True, join_faction=True)
    for entry in opening['people']:
        pid = entry['person_id']
        era = data['era_assignments'][pid]
        if entry['start'] != [RETURN_YEAR, 1]:
            raise ValueError(f'{data["id"]}: invalid envoy return date: {pid}')
        era['appearance_plan']['mission_departure_year'] = DEPARTURE_YEAR
        if era['status'] == 'serving':
            if data['initial_owners'].get(city) != owner:
                raise ValueError(f'{data["id"]}: opening envoy post is outside Wu: {city}')
            data['initial_officers'].append(dict(
                person_id=pid, city=city, troops=0, ruler=False,
                resolve_death_year=era['death_year_resolved']))


def place_faction_officers(data, present, people):
    """Install the opening garrison and suppress any prior free placement."""
    for record, period in present:
        faction = record['faction']
        owner, city = faction['id'], faction['city']
        sources = record['history']['sources']
        for pid in record.get('future_in_capital', ()):
            era = data['era_assignments'][pid]
            plan = era['appearance_plan']
            if plan['status'] in ('future', 'future_free'):
                data['appearance_locations'][pid] = city
                plan['city'] = city
                era['city'] = city
                if isinstance(era.get('posting_reference'), dict):
                    era['posting_reference']['city'] = city
                for window in data['appearance_windows'].get(pid, ()):
                    window['city'] = city
        dated = {row['person_id']: row for row in record.get('officer_chronology', ())
                 if data['era_assignments'][row['person_id']]['status'] == 'serving'}
        officers = [{'person_id': period['ruler'], 'troops': period['troops']}, *period.get('officers', []),
                    *dated.values()]
        ids = {row['person_id'] for row in officers}
        if len(ids) != len(officers) or any(row.get('ruler') for row in data['initial_officers'] if row['person_id'] in ids):
            raise ValueError(f'{data["id"]}: invalid historical faction opening roster for {owner}')
        data['initial_officers'] = [row for row in data['initial_officers'] if row['person_id'] not in ids]
        data['initial_free_officers'] = [row for row in data['initial_free_officers'] if row['person_id'] not in ids]
        for entry in officers:
            pid, troops = entry['person_id'], entry['troops']
            person = people[pid]
            year = data['start_year']
            if not person['service_year'] <= year <= person['death_year'] or type(troops) is not int or not 0 <= troops <= 10000:
                raise ValueError(f'{data["id"]}: invalid historical opening officer: {pid}')
            resolve = year == person['death_year']
            data['initial_officers'].append(dict(person_id=pid, city=city, troops=troops,
                                                 ruler=pid == period['ruler'], resolve_death_year=resolve))
            data['appearance_locations'][pid] = city
            if pid not in dated:
                data['era_assignments'][pid] = opening_era(data, person, owner, city, sources, period['note'], 'serving',
                                                           [year, data['start_month']], [person['death_year'], 12], resolve)
            data['city_history'][city]['garrisons'].append(dict(person_id=pid, name=person['name'], basis=BASIS))
