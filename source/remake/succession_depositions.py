"""Conditional historical accessions following the removal of a living ruler."""

from . import officer_relations


_DEPOSITIONS = {
    # Take the enthronement month when the records give separate removal and accession dates.
    (254, 10): ('wei', 'san14-candidate-0529', 'san14-candidate-0346', 'san14-candidate-0530'),  # 三國志卷04
    (258, 10): ('wu', 'san14-candidate-0578', 'san14-candidate-0569', 'san14-candidate-0548'),  # 三國志卷48
}


def process(game, state):
    """Apply a documented change if the court still matches at the month boundary."""
    rule = _DEPOSITIONS.get((state.year, state.month))
    if rule is None:
        return
    faction, previous, regent, successor = rule
    ruler_id, regent_id, successor_id = (game.catalog.ids.get(pid) for pid in (previous, regent, successor))
    ruler, official = (state.officers.get(ident) for ident in (ruler_id, regent_id))
    if faction == 'wu' and ruler is not None and ruler.faction_id == 'sun_jian':
        faction = 'sun_jian'
    if (faction in state.extension['pending_succession']
            or not any(city.owner == faction for city in state.cities.values())):
        return
    leaders = state.extension['leaders']
    if ruler_id is None or successor_id is None or leaders.get(faction) != ruler_id:
        return
    if not all(officer is not None and officer.alive and officer.faction_id == faction
               for officer in (ruler, official)):
        return
    marching = game._march_ids(state)
    if ruler_id in marching or successor_id in marching:
        return

    from .succession import admit_nominee
    if not admit_nominee(game, state, faction, successor_id):
        return
    leaders[faction] = successor_id
    ruler.loyalty = min(99, ruler.loyalty)
    state.officers[successor_id].loyalty = 100
    officer_relations.apply_faction(game, state, faction)
    game._note(state, f'{game.person_name(state, successor_id)}接任势力主将。')
