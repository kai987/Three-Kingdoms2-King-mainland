use crate::{field, hazards, number, numeric, string, Result};
use serde_json::{json, Map, Value};
use std::borrow::Borrow;
use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet, BinaryHeap};

#[derive(Default)]
struct Cities {
    order: Vec<String>,
    owners: BTreeMap<String, Value>,
}

impl Cities {
    fn read(request: &Value) -> Result<Self> {
        let mut cities = Self::default();
        let rows = field(request, "cities")?;
        if rows.is_null() {
            return Ok(cities);
        }
        for row in rows.as_array().ok_or("cities must be an array")? {
            let id = string(row, "id")?.to_owned();
            let owner = field(row, "owner")?.clone();
            if cities.owners.insert(id.clone(), owner).is_some() {
                return Err("Duplicate city ID".into());
            }
            cities.order.push(id);
        }
        Ok(cities)
    }
}

fn rows<'a>(data: &'a Value, name: &str) -> Result<&'a [Value]> {
    match data.get(name) {
        Some(Value::Array(rows)) => Ok(rows),
        None => Ok(&[]),
        _ => Err(format!("{name} must be an array")),
    }
}

fn discovered(request: &Value) -> Result<BTreeSet<&str>> {
    match request.get("discovered") {
        None => Ok(BTreeSet::new()),
        Some(Value::Array(items)) => items
            .iter()
            .map(|v| {
                v.as_str()
                    .ok_or_else(|| "discovered IDs must be strings".into())
            })
            .collect(),
        _ => Err("discovered must be an array".into()),
    }
}

fn known_routes<'a>(data: &'a Value, request: &Value, active: &Cities) -> Result<Vec<&'a Value>> {
    let mut declared: Vec<_> = rows(data, "travel_routes")?.iter().collect();
    let found = discovered(request)?;
    for row in rows(data, "exploration_routes")? {
        if found.contains(string(row, "id")?) {
            declared.push(row);
        }
    }
    let year = request.get("year").and_then(Value::as_i64);
    let month = request.get("month").and_then(Value::as_i64).unwrap_or(1);
    let mut result = vec![];
    for route in declared {
        if let (Some(year), Some(Value::Array(closures))) = (year, route.get("closures")) {
            let date = (year, month);
            let mut closed = false;
            for period in closures {
                let bound = |key: &str| -> Result<(i64, i64)> {
                    let parts = field(period, key)?
                        .as_array()
                        .ok_or("Invalid road closure")?;
                    if parts.len() != 2 {
                        return Err("Invalid road closure".into());
                    }
                    Ok((
                        parts[0].as_i64().ok_or("Invalid closure year")?,
                        parts[1].as_i64().ok_or("Invalid closure month")?,
                    ))
                };
                closed |= bound("from")? <= date && date < bound("to")?;
            }
            if closed {
                continue;
            }
        }
        if let (Some(year), Some(window)) = (year, route.get("availability")) {
            let date = (year, month);
            let bound = |key: &str| -> Result<Option<(i64, i64)>> {
                window
                    .get(key)
                    .map(|value| {
                        let parts = value.as_array().ok_or("Invalid road availability")?;
                        if parts.len() != 2 {
                            return Err("Invalid road availability".into());
                        }
                        Ok((
                            parts[0].as_i64().ok_or("Invalid road year")?,
                            parts[1].as_i64().ok_or("Invalid road month")?,
                        ))
                    })
                    .transpose()
            };
            if bound("from")?.is_some_and(|start| date < start)
                || bound("to")?.is_some_and(|end| date >= end)
            {
                continue;
            }
        }
        if let Some(Value::Array(variants)) = route.get("transit_variants") {
            for section in variants {
                let a = string(section, "from")?;
                let b = string(section, "to")?;
                let via = field(section, "via")?
                    .as_array()
                    .ok_or("Invalid road transit")?;
                if active.owners.contains_key(a)
                    && active.owners.contains_key(b)
                    && !via
                        .iter()
                        .any(|id| id.as_str().is_some_and(|id| active.owners.contains_key(id)))
                {
                    result.push(section);
                }
            }
        } else {
            result.push(route);
        }
    }
    Ok(result)
}

fn is_pair(route: &Value, source: &str, target: &str) -> Result<bool> {
    let (a, b) = (string(route, "from")?, string(route, "to")?);
    // Python's unordered set comparison allows identical endpoints here.
    Ok((source == a && target == b) || (source == b && target == a))
}

fn other<'a>(route: &'a Value, here: &str) -> Result<Option<&'a str>> {
    let (a, b) = (string(route, "from")?, string(route, "to")?);
    Ok(if a == here {
        Some(b)
    } else if b == here {
        Some(a)
    } else {
        None
    })
}

fn exploration<'a>(data: &'a Value, source: &str, target: &str) -> Result<Option<&'a Value>> {
    let coastal = data
        .get("travel_hazards")
        .and_then(|p| p.get("coastal_cities"))
        .and_then(Value::as_array);
    if source == target
        || !coastal.is_some_and(|v| {
            v.iter().any(|v| v.as_str() == Some(source))
                && v.iter().any(|v| v.as_str() == Some(target))
        })
    {
        return Ok(None);
    }
    for route in rows(data, "exploration_routes")? {
        if is_pair(route, source, target)? {
            return Ok(Some(route));
        }
    }
    Ok(None)
}

fn python_equal(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Number(a), Value::Number(b)) => a.as_f64() == b.as_f64(),
        (Value::Array(a), Value::Array(b)) => {
            a.len() == b.len() && a.iter().zip(b).all(|(a, b)| python_equal(a, b))
        }
        (Value::Object(a), Value::Object(b)) => {
            a.len() == b.len()
                && a.iter()
                    .all(|(k, a)| b.get(k).is_some_and(|b| python_equal(a, b)))
        }
        _ => a == b,
    }
}

struct Entry<Leg> {
    days: f64,
    distance: f64,
    city: String,
    serial: u64,
    path: Vec<String>,
    legs: Vec<Leg>,
}

impl<Leg> PartialEq for Entry<Leg> {
    fn eq(&self, other: &Self) -> bool {
        self.cmp(other) == Ordering::Equal
    }
}
impl<Leg> Eq for Entry<Leg> {}
impl<Leg> PartialOrd for Entry<Leg> {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}
impl<Leg> Ord for Entry<Leg> {
    fn cmp(&self, other: &Self) -> Ordering {
        // BinaryHeap is a max heap; reverse Python heapq's complete key.
        other
            .days
            .total_cmp(&self.days)
            .then_with(|| other.distance.total_cmp(&self.distance))
            .then_with(|| other.city.cmp(&self.city))
            .then_with(|| other.serial.cmp(&self.serial))
    }
}

fn initial<Leg>(source: &str) -> BinaryHeap<Entry<Leg>> {
    BinaryHeap::from([Entry {
        days: 0.0,
        distance: 0.0,
        city: source.into(),
        serial: 0,
        path: vec![source.into()],
        legs: vec![],
    }])
}

fn can_transit(owner: Option<&Value>, player: &Value) -> bool {
    owner.is_some_and(|owner| owner == player || owner.as_str() == Some("neutral"))
}

fn enqueue<Leg: Borrow<Value> + Clone>(
    queue: &mut BinaryHeap<Entry<Leg>>,
    current: &Entry<Leg>,
    target: &str,
    leg: Leg,
    serial: &mut u64,
) -> Result<()> {
    let mut path = current.path.clone();
    path.push(target.into());
    let mut legs = current.legs.clone();
    let (leg_days, leg_distance) = score(leg.borrow())?;
    let days = current.days + leg_days;
    let distance = current.distance + leg_distance;
    if !days.is_finite() || !distance.is_finite() {
        return Err("Route total is too large".into());
    }
    legs.push(leg);
    *serial = serial.checked_add(1).ok_or("Route queue is too large")?;
    queue.push(Entry {
        days,
        distance,
        city: target.into(),
        serial: *serial,
        path,
        legs,
    });
    Ok(())
}

fn quote<Leg: Borrow<Value>>(path: &[String], legs: &[Leg]) -> Result<Value> {
    let (mut days, mut distance) = (0.0, 0.0);
    let mut whole_days = true;
    let mut modes = BTreeSet::new();
    for leg in legs {
        let leg = leg.borrow();
        let d = field(leg, "days")?;
        let km = field(leg, "distance_km")?;
        days += number(d, "Invalid route days")?;
        distance += number(km, "Invalid route distance")?;
        whole_days &= d.as_number().is_some_and(|v| !v.is_f64());
        modes.insert(string(leg, "mode")?);
    }
    // Rust's decimal formatter rounds the original binary float to nearest,
    // ties to even, matching Python round(value, 1), including e.g. 1.25.
    let rounded: f64 = format!("{distance:.1}")
        .parse()
        .map_err(|_| "Invalid route distance")?;
    let mut quote = json!({"path":path,"days":numeric(days, whole_days)?,
        "months":numeric((days / 30.0).ceil().max(1.0), true)?,
        "turns":numeric((days / 10.0).ceil().max(1.0), true)?,
        "distance_km":numeric(rounded, true)?,
        "grain_per_officer":5 * legs.len(),"modes":modes});
    quote["routes"] = Value::Array(legs.iter().map(|leg| leg.borrow().clone()).collect());
    Ok(quote)
}

fn score(leg: &Value) -> Result<(f64, f64)> {
    Ok((
        number(field(leg, "days")?, "Invalid route days")?,
        number(field(leg, "distance_km")?, "Invalid route distance")?,
    ))
}

fn best<Leg: Borrow<Value>>(
    legs: impl IntoIterator<Item = Leg>,
    with_id: bool,
) -> Result<Option<Leg>> {
    let mut winner: Option<(Leg, f64, f64, String)> = None;
    for leg in legs {
        let (days, distance) = score(leg.borrow())?;
        let id = if with_id {
            string(leg.borrow(), "id")?.to_owned()
        } else {
            String::new()
        };
        let replace = winner.as_ref().is_none_or(|(_, d, km, old_id)| {
            days.total_cmp(d)
                .then_with(|| distance.total_cmp(km))
                .then_with(|| id.cmp(old_id))
                == Ordering::Less
        });
        if replace {
            winner = Some((leg, days, distance, id));
        }
    }
    Ok(winner.map(|(leg, _, _, _)| leg))
}

pub(crate) fn path(data: &Value, request: &Value) -> Result<Value> {
    let mode = match request.get("mode") {
        None => "fastest",
        Some(value) => value.as_str().ok_or("请选择有效的行军路线。")?,
    };
    if !["fastest", "land", "river", "sea", "special", "explore"].contains(&mode) {
        return Err("请选择有效的行军路线。".into());
    }
    let (source, target) = (string(request, "source")?, string(request, "target")?);
    let owner = field(request, "owner")?;
    let cities = Cities::read(request)?;
    let adjacent = request
        .get("adjacent")
        .and_then(Value::as_bool)
        .unwrap_or(false);
    if source == target
        || !cities.owners.contains_key(source)
        || !cities.owners.contains_key(target)
        || !adjacent && cities.owners.get(target) != Some(owner)
    {
        return Ok(Value::Null);
    }
    let routes = known_routes(data, request, &cities)?;
    let month = request.get("month").unwrap_or(&Value::Null);
    if ["river", "sea", "special", "explore"].contains(&mode) {
        let mut candidates = vec![];
        if mode == "explore" {
            let Some(raw) = exploration(data, source, target)? else {
                return Ok(Value::Null);
            };
            for row in &routes {
                if row.get("mode").and_then(Value::as_str) == Some("sea")
                    && is_pair(row, source, target)?
                {
                    return Ok(Value::Null);
                }
            }
            candidates.push(raw);
        } else {
            for row in &routes {
                let suitable = if ["river", "sea"].contains(&mode) {
                    row.get("mode").and_then(Value::as_str) == Some(mode)
                } else {
                    row.get("special")
                        .and_then(Value::as_str)
                        .is_some_and(|s| ["yinping", "ziwu"].contains(&s))
                };
                if suitable && is_pair(row, source, target)? {
                    candidates.push(*row);
                }
            }
            if mode == "special"
                && ((source == "yinping" && target == "shujun")
                    || (source == "shujun" && target == "yinping"))
            {
                for row in &routes {
                    if row.get("mode").and_then(Value::as_str) == Some("land")
                        && is_pair(row, source, target)?
                        && !candidates.iter().any(|v| python_equal(v, row))
                    {
                        candidates.push(*row);
                    }
                }
            }
        }
        let mut legs = vec![];
        for raw in candidates {
            if hazards::allowed(data, raw, source, target)? {
                legs.push(hazards::evaluate(data, raw, source, target, month)?);
            }
        }
        return match best(legs, true)? {
            Some(leg) => quote(&[source.into(), target.into()], &[leg]),
            None => Ok(Value::Null),
        };
    }
    let mut queue = initial(source);
    let mut serial = 0;
    let mut seen = BTreeSet::new();
    while let Some(current) = queue.pop() {
        if !seen.insert(current.city.clone()) {
            continue;
        }
        if current.city == target && !current.legs.is_empty() {
            return quote(&current.path, &current.legs);
        }
        for raw in &routes {
            let Some(next) = other(raw, &current.city)? else {
                continue;
            };
            if mode == "land" && raw.get("mode").and_then(Value::as_str) != Some("land") {
                continue;
            }
            if !cities.owners.contains_key(next) || seen.contains(next) {
                continue;
            }
            if adjacent && (current.city != source || next != target) {
                continue;
            }
            if !adjacent && !can_transit(cities.owners.get(next), owner) {
                continue;
            }
            if !hazards::allowed(data, raw, &current.city, next)? {
                continue;
            }
            let leg = hazards::evaluate(data, raw, &current.city, next, month)?;
            enqueue(&mut queue, &current, next, leg, &mut serial)?;
        }
    }
    Ok(Value::Null)
}

fn special(leg: &Value) -> bool {
    leg.get("hazard")
        .and_then(|h| h.get("kind"))
        .and_then(Value::as_str)
        .is_some_and(|kind| ["yinping", "ziwu_rain", "ziwu_dry"].contains(&kind))
}

fn insert_direct<'a>(
    quotes: &mut Map<String, Value>,
    source: &str,
    target: &str,
    mode: &str,
    options: impl IntoIterator<Item = &'a Value>,
) -> Result<()> {
    if let Some(leg) = best(options, false)? {
        quotes.insert(
            format!("{source}:{target}:{mode}"),
            quote(&[source.into(), target.into()], &[leg])?,
        );
    }
    Ok(())
}

pub(crate) fn batch(data: &Value, request: &Value) -> Result<Value> {
    let cities = Cities::read(request)?;
    let player = field(request, "player")?;
    let mut quotes = Map::new();
    if cities.order.is_empty() {
        return Ok(Value::Object(quotes));
    }
    let routes = known_routes(data, request, &cities)?;
    let month = request.get("month").unwrap_or(&Value::Null);
    let mut adjacency: BTreeMap<String, Vec<Value>> =
        cities.order.iter().map(|id| (id.clone(), vec![])).collect();
    for raw in &routes {
        let (a, b) = (string(raw, "from")?, string(raw, "to")?);
        for (a, b) in [(a, b), (b, a)] {
            if cities.owners.contains_key(a)
                && cities.owners.contains_key(b)
                && hazards::allowed(data, raw, a, b)?
            {
                if let Some(legs) = adjacency.get_mut(a) {
                    legs.push(hazards::evaluate(data, raw, a, b, month)?);
                }
            }
        }
    }
    let mut explorations: BTreeMap<String, Vec<Value>> =
        cities.order.iter().map(|id| (id.clone(), vec![])).collect();
    for raw in rows(data, "exploration_routes")? {
        let (a, b) = (string(raw, "from")?, string(raw, "to")?);
        let mut known = false;
        for route in &routes {
            known |=
                route.get("mode").and_then(Value::as_str) == Some("sea") && is_pair(route, a, b)?;
        }
        if known {
            continue;
        }
        for (a, b) in [(a, b), (b, a)] {
            if cities.owners.contains_key(a)
                && cities.owners.contains_key(b)
                && exploration(data, a, b)?.is_some_and(|first| python_equal(raw, first))
            {
                if let Some(legs) = explorations.get_mut(a) {
                    legs.push(hazards::evaluate(data, raw, a, b, month)?);
                }
            }
        }
    }
    for source in &cities.order {
        if cities.owners.get(source) != Some(player) {
            continue;
        }
        for mode in ["fastest", "land"] {
            let mut queue = initial(source);
            let mut serial = 0;
            let mut seen = BTreeSet::new();
            while let Some(current) = queue.pop() {
                if !seen.insert(current.city.clone()) {
                    continue;
                }
                // Neutral cities connect friendly destinations; they are not
                // themselves transfer destinations or remote attack targets.
                if !current.legs.is_empty() && cities.owners.get(&current.city) == Some(player) {
                    quotes.insert(
                        format!("{source}:{}:{mode}", current.city),
                        quote(&current.path, &current.legs)?,
                    );
                }
                if let Some(legs) = adjacency.get(&current.city) {
                    for leg in legs {
                        let target = string(leg, "to")?;
                        if seen.contains(target)
                            || !can_transit(cities.owners.get(target), player)
                            || mode == "land" && string(leg, "mode")? != "land"
                        {
                            continue;
                        }
                        // The batch owns each evaluated direction once. Search
                        // entries borrow those legs until a quote is emitted.
                        enqueue(&mut queue, &current, target, leg, &mut serial)?;
                    }
                }
            }
            let legs = &adjacency[source];
            let targets: BTreeSet<_> = legs
                .iter()
                .filter_map(|leg| leg.get("to").and_then(Value::as_str))
                .filter(|target| cities.owners.get(*target) != Some(player))
                .collect();
            for target in targets {
                let options = legs.iter().filter(|leg| {
                    leg.get("to").and_then(Value::as_str) == Some(target)
                        && (mode != "land"
                            || leg.get("mode").and_then(Value::as_str) == Some("land"))
                });
                insert_direct(&mut quotes, source, target, mode, options)?;
            }
        }
        for mode in ["river", "sea", "special"] {
            let legs = &adjacency[source];
            let suitable = |leg: &&Value| {
                if ["river", "sea"].contains(&mode) {
                    leg.get("mode").and_then(Value::as_str) == Some(mode)
                } else {
                    special(leg)
                }
            };
            let targets: BTreeSet<_> = legs
                .iter()
                .filter(suitable)
                .filter_map(|leg| leg.get("to").and_then(Value::as_str))
                .collect();
            for target in targets {
                let options = legs
                    .iter()
                    .filter(suitable)
                    .filter(|leg| leg.get("to").and_then(Value::as_str) == Some(target));
                insert_direct(&mut quotes, source, target, mode, options)?;
            }
        }
        for leg in &explorations[source] {
            let target = string(leg, "to")?;
            quotes.insert(
                format!("{source}:{target}:explore"),
                quote(&[source.clone(), target.into()], std::slice::from_ref(leg))?,
            );
        }
    }
    Ok(Value::Object(quotes))
}
