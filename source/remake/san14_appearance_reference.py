"""Reviewed SAN14 PK debut years for the 1,000 stable base names.

Source: https://www.nobuwiki.org/san/game_14/s14_01
Order is the project's san14-candidate ID, not web-table row order.
Same-name officers were resolved by their distinct death years and home cities.
周喁 is 周㬂 and 党均 is 黨均 on this source.

SHA-256 of the reviewed name, debut, death and city rows in ID order:
b17cefb2126498c61ed7a7254449273b5321bacfeab384e0ede9aa9d4c52f774
"""

from .officers import YearState

YEARS = (
    217, 191, 196, 223, 189, 190, 195, 184, 196, 213, 230, 224, 212, 184, 217, 184, 223, 184, 184, 239,
    184, 195, 210, 184, 184, 228, 199, 184, 190, 184, 189, 184, 191, 193, 184, 187, 187, 187, 191, 192,
    196, 184, 187, 196, 219, 236, 184, 239, 225, 231, 213, 240, 193, 238, 187, 184, 187, 253, 209, 225,
    203, 184, 186, 236, 184, 219, 186, 207, 229, 217, 189, 216, 190, 184, 198, 186, 191, 192, 201, 184,
    184, 197, 209, 184, 184, 195, 236, 223, 199, 184, 184, 184, 201, 191, 189, 220, 184, 184, 197, 204,
    202, 188, 184, 210, 184, 253, 209, 184, 209, 221, 206, 218, 217, 184, 194, 224, 222, 219, 223, 200,
    205, 199, 197, 184, 216, 215, 202, 221, 184, 231, 245, 184, 199, 189, 216, 199, 208, 210, 241, 221,
    191, 184, 223, 184, 233, 184, 184, 184, 184, 184, 211, 220, 195, 225, 238, 184, 218, 184, 184, 184,
    213, 214, 189, 192, 184, 184, 184, 184, 184, 220, 201, 184, 184, 189, 232, 184, 184, 199, 193, 218,
    192, 184, 200, 184, 184, 184, 192, 189, 194, 193, 184, 184, 184, 240, 201, 184, 201, 253, 184, 251,
    184, 184, 225, 197, 196, 184, 184, 184, 184, 227, 184, 189, 184, 184, 189, 189, 184, 192, 184, 197,
    217, 184, 184, 231, 184, 191, 240, 193, 217, 227, 184, 243, 184, 184, 188, 189, 184, 225, 184, 184,
    185, 233, 184, 194, 201, 205, 184, 187, 208, 186, 245, 184, 193, 186, 213, 184, 222, 184, 194, 184,
    184, 219, 188, 186, 214, 184, 190, 184, 184, 184, 184, 207, 210, 189, 186, 219, 184, 241, 184, 184,
    184, 219, 261, 253, 184, 184, 184, 205, 184, 253, 235, 184, 206, 214, 196, 188, 184, 219, 224, 198,
    185, 223, 196, 219, 243, 188, 217, 185, 198, 190, 197, 184, 236, 197, 189, 239, 184, 184, 185, 188,
    184, 207, 207, 187, 184, 184, 184, 196, 251, 184, 184, 184, 190, 184, 184, 194, 184, 245, 234, 184,
    184, 196, 184, 198, 250, 222, 192, 225, 241, 199, 219, 262, 190, 184, 187, 219, 184, 197, 184, 206,
    215, 263, 220, 184, 184, 184, 184, 252, 211, 196, 184, 241, 189, 226, 184, 209, 209, 210, 189, 197,
    196, 209, 214, 195, 209, 196, 184, 220, 196, 184, 206, 189, 184, 206, 184, 226, 244, 228, 184, 185,
    184, 184, 238, 238, 207, 239, 194, 215, 184, 184, 194, 187, 236, 220, 244, 184, 200, 207, 214, 243,
    246, 230, 220, 184, 233, 184, 196, 186, 191, 217, 218, 195, 208, 237, 260, 255, 241, 225, 221, 208,
    184, 188, 190, 197, 226, 206, 202, 201, 196, 191, 190, 215, 253, 191, 209, 191, 205, 253, 200, 189,
    224, 194, 207, 184, 189, 184, 192, 211, 184, 184, 184, 184, 184, 184, 189, 244, 190, 233, 207, 233,
    237, 211, 235, 206, 192, 191, 184, 244, 209, 188, 226, 245, 184, 187, 227, 202, 218, 193, 190, 213,
    219, 213, 258, 224, 189, 226, 184, 194, 208, 189, 188, 184, 196, 189, 204, 206, 204, 187, 184, 210,
    184, 221, 207, 184, 184, 200, 184, 209, 239, 254, 209, 211, 221, 198, 184, 195, 191, 184, 184, 237,
    231, 238, 184, 216, 184, 209, 246, 249, 200, 249, 184, 184, 196, 256, 200, 227, 189, 203, 196, 249,
    238, 207, 190, 217, 207, 253, 184, 184, 250, 223, 241, 184, 245, 194, 191, 198, 227, 250, 204, 218,
    201, 216, 192, 194, 207, 185, 217, 218, 207, 217, 207, 184, 200, 184, 187, 187, 191, 184, 191, 194,
    184, 192, 197, 210, 251, 184, 184, 189, 186, 221, 220, 184, 209, 184, 195, 209, 194, 184, 224, 184,
    195, 221, 210, 239, 184, 215, 184, 184, 238, 203, 194, 189, 216, 197, 184, 213, 188, 184, 219, 194,
    194, 188, 201, 209, 200, 193, 184, 253, 223, 228, 187, 209, 184, 187, 184, 184, 244, 212, 184, 184,
    184, 207, 188, 184, 202, 184, 184, 203, 203, 184, 184, 194, 186, 184, 233, 235, 252, 196, 215, 210,
    189, 224, 188, 194, 218, 195, 184, 184, 184, 184, 187, 203, 184, 184, 217, 184, 201, 204, 184, 220,
    192, 189, 184, 215, 191, 207, 217, 210, 184, 184, 237, 188, 184, 195, 189, 217, 221, 214, 187, 216,
    189, 248, 223, 184, 208, 246, 185, 193, 201, 225, 188, 247, 252, 184, 184, 184, 244, 240, 217, 184,
    190, 254, 184, 184, 202, 184, 191, 184, 194, 191, 184, 241, 253, 184, 243, 202, 197, 185, 189, 192,
    219, 184, 184, 215, 209, 197, 205, 205, 189, 193, 184, 240, 245, 206, 254, 209, 224, 200, 231, 193,
    196, 184, 184, 184, 184, 184, 212, 215, 207, 200, 195, 194, 184, 218, 188, 211, 186, 184, 197, 194,
    201, 200, 228, 187, 201, 230, 184, 207, 236, 217, 241, 184, 184, 197, 184, 184, 197, 184, 184, 219,
    217, 184, 184, 200, 220, 184, 195, 208, 184, 184, 202, 208, 230, 194, 184, 243, 216, 196, 236, 190,
    199, 189, 221, 184, 212, 207, 187, 235, 191, 215, 199, 197, 184, 186, 200, 209, 214, 228, 239, 240,
    184, 191, 196, 192, 184, 194, 191, 186, 189, 245, 221, 203, 242, 184, 225, 189, 184, 223, 197, 184,
    213, 184, 194, 196, 184, 191, 184, 184, 207, 237, 206, 194, 184, 184, 195, 234, 220, 224, 217, 240,
    206, 202, 207, 187, 223, 240, 184, 184, 220, 207, 187, 204, 189, 184, 194, 219, 216, 223, 184, 191,
    238, 184, 208, 224, 184, 190, 184, 189, 188, 197, 184, 184, 184, 202, 202, 184, 198, 184, 212, 234,
    252, 208, 238, 184, 221, 207, 184, 208, 187, 205, 188, 184, 184, 195, 215, 184, 232, 184, 206, 195,
    184, 193, 184, 225, 226, 188, 217, 184, 188, 184, 187, 217, 184, 203, 194, 200, 214, 206, 210, 192,
    201, 184, 184, 184, 184, 188, 184, 193, 196, 216, 218, 205, 207, 184, 242, 198, 191, 226, 193, 184,
)


def apply(data):
    """Overlay the reviewed debut rule without changing the scenario edition or its save hash."""
    if (not data['id'].startswith('mainland') or
            not data.get('placement_completion', {}).get('complete') or
            len(data['people']) < 1083):
        return {}
    opening = [data['start_year'], data['start_month']]
    year = opening[0]
    active = set(data['active_cities'])
    already_placed = {row['person_id'] for key in ('initial_officers', 'initial_free_officers')
                      for row in data[key]}
    changes = {}
    for person in data['people']:
        pid = person['person_id']
        ordinal = pid.removeprefix('san14-candidate-')
        if pid.startswith('san14-candidate-') and ordinal.isdecimal() and 1 <= int(ordinal) <= len(YEARS):
            new = YEARS[int(ordinal) - 1]
        else:
            new = person['birth_year'] + 15
        old = person['service_year']
        if new == old:
            continue
        if not person['birth_year'] <= new <= person['death_year'] or (pid in already_placed and new > year):
            raise ValueError(f'{data["id"]}: debut conflicts with the reviewed opening or lifespan for {pid}')
        person['service_year'] = new
        changes[pid] = (old, new)

        era = data['era_assignments'][pid]
        plan = era['appearance_plan']
        if person['birth_year'] <= year <= person['death_year'] and (old <= year) != (new <= year):
            era['year_state'] = (YearState.NOT_APPEARED.value if year < new else
                                 YearState.DEATH_YEAR_REVIEW.value if year == person['death_year']
                                 else YearState.AVAILABLE.value)
        # Named rulers, missions and appointments keep their explicit dates.
        # A generic free-officer window uses the revised debut boundary.
        if (plan['status'] != 'future_free' or plan['basis'] == 'reviewed_historical_faction_opening'
                or not plan['start'] or plan['start'][0] != old):
            continue
        city = plan['city']
        founding = data['city_foundings'].get(city)
        start = max([new, 1], [founding['year'], founding['month']]) if founding else [new, 1]
        if start > plan['end']:
            raise ValueError(f'{data["id"]}: invalid debut window for {pid}')
        for window in data['appearance_windows'][pid]:
            if window['start'] == plan['start'] and window['city'] == city and not window.get('faction'):
                window['start'] = start
                if start <= opening <= window['end'] and city in active:
                    # Record it in the opening list as well as the time window
                    # so scenario selection and a played opening agree.
                    resolve = window.get('resolve_death_year', False)
                    if year != person['death_year'] or resolve:
                        data['initial_free_officers'].append(dict(person_id=pid, city=city,
                                                                  resolve_death_year=resolve))
                        era.update(status='free', city=city, death_year_resolved=year == person['death_year'])
                        plan['status'] = 'free'
                plan['start'] = start
                break
    future = sum(era['appearance_plan']['status'] in ('future', 'future_free')
                 for era in data['era_assignments'].values())
    data['coverage'].update(initial_free=len(data['initial_free_officers']), future_plans=future)
    data['placement_completion']['future_plans'] = future
    return changes
