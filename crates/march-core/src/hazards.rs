use crate::{field, integer, normalized, number, numeric, string, truthy, Result};
use serde_json::{json, Value};

const RATIO_ERROR: &str = "Survival ratio must be integers with0<=n<=d andd>0";
const TROOPS_ERROR: &str = "Troop counts must be nonnegative integers";

fn pair(route: &Value, source: &str, target: &str) -> Result<bool> {
    let a = string(route, "from")?;
    let b = string(route, "to")?;
    Ok(source != target && ((source == a && target == b) || (source == b && target == a)))
}

fn text<'a>(value: &'a Value, key: &str, default: &'a str) -> Result<&'a str> {
    match value.get(key) {
        Some(v) => v.as_str().ok_or_else(|| format!("{key} must be a string")),
        None => Ok(default),
    }
}

fn num(value: &Value, key: &str, default: f64) -> Result<f64> {
    match value.get(key) {
        Some(v) => number(v, &format!("{key} must be numeric")),
        None => Ok(default),
    }
}

fn ratio(numerator: &Value, denominator: &Value) -> Result<(u64, u64)> {
    let n = integer(numerator, RATIO_ERROR)?;
    let d = integer(denominator, RATIO_ERROR)?;
    if d == 0 || n > d {
        return Err(RATIO_ERROR.into());
    }
    Ok((n, d))
}

fn values(troops: &Value) -> Result<Vec<u64>> {
    troops
        .as_array()
        .ok_or(TROOPS_ERROR)?
        .iter()
        .map(|v| integer(v, TROOPS_ERROR))
        .collect()
}

/// Largest-remainder distribution, with the original roster order as tie break.
pub(crate) fn allocate(troops: &[u64], numerator: u64, denominator: u64) -> Result<Vec<u64>> {
    if denominator == 0 || numerator > denominator {
        return Err(RATIO_ERROR.into());
    }
    let mut result = Vec::with_capacity(troops.len());
    let mut remainders = Vec::with_capacity(troops.len());
    let mut total = 0_u128;
    let mut allocated = 0_u128;
    for (index, value) in troops.iter().copied().enumerate() {
        total = total
            .checked_add(value as u128)
            .ok_or("Troop total is too large")?;
        let product = value as u128 * numerator as u128;
        let whole = product / denominator as u128;
        allocated += whole;
        result.push(whole as u64);
        remainders.push((product % denominator as u128, index));
    }
    let required = total
        .checked_mul(numerator as u128)
        .ok_or("Troop total is too large")?
        / denominator as u128;
    let missing = usize::try_from(required - allocated).map_err(|_| "Troop total is too large")?;
    remainders.sort_by(|(a, ai), (b, bi)| b.cmp(a).then_with(|| ai.cmp(bi)));
    for (_, index) in remainders.into_iter().take(missing) {
        result[index] += 1;
    }
    Ok(result)
}

pub(crate) fn allocate_request(request: &Value) -> Result<Value> {
    let (n, d) = ratio(field(request, "numerator")?, field(request, "denominator")?)?;
    Ok(json!(allocate(&values(field(request, "troops")?)?, n, d)?))
}

pub(crate) fn allowed(data: &Value, route: &Value, source: &str, target: &str) -> Result<bool> {
    if !pair(route, source, target)? {
        return Ok(false);
    }
    let yinping = &data["travel_hazards"]["yinping"];
    let start = text(yinping, "from", "yinping")?;
    let end = text(yinping, "to", "shujun")?;
    if route.get("mode").and_then(Value::as_str) == Some("land")
        && ((source == start && target == end) || (source == end && target == start))
    {
        return Ok(source == start && target == end);
    }
    Ok(true)
}

fn fixed(
    kind: &str,
    label: &str,
    n: u64,
    d: u64,
    month: u64,
    season: Option<&str>,
) -> Result<Value> {
    let percent = numeric(((d - n) as u128 * 100) as f64 / d as f64, true)?;
    Ok(
        json!({"kind":kind,"label":label,"season":season,"wind":null,
        "month":month,"survival_numerator":n,"survival_denominator":d,
        "loss_percent":percent,"loss_percent_min":percent,"loss_percent_max":percent}),
    )
}

fn in_months(rule: &Value, name: &str, month: u64, default: &[u64]) -> Result<bool> {
    if let Some(items) = rule.get(name) {
        let items = items
            .as_array()
            .ok_or_else(|| format!("{name} must be an array"))?;
        Ok(items.iter().any(|v| v.as_u64() == Some(month)))
    } else {
        Ok(default.contains(&month))
    }
}

fn coordinates(data: &Value, city: &str) -> Result<(f64, f64)> {
    let coords = data
        .get("city_coordinates")
        .and_then(|v| v.get(city))
        .and_then(Value::as_array)
        .ok_or_else(|| format!("Missing coordinates: {city}"))?;
    if coords.len() != 2 {
        return Err(format!("Invalid coordinates: {city}"));
    }
    Ok((
        number(&coords[0], "Invalid longitude")?,
        number(&coords[1], "Invalid latitude")?,
    ))
}

fn river_number(value: Option<&Value>, error: &str, zero: bool) -> Result<f64> {
    let value = number(value.unwrap_or(&Value::Null), error)?;
    if if zero { value < 0.0 } else { value <= 0.0 } {
        return Err(error.into());
    }
    Ok(value)
}

/// Surveyed river reaches have directional current, never ocean weather.
fn river(rules: &Value, route: &Value, mut leg: Value, source: &str, plain: f64) -> Result<Value> {
    let segments = route
        .get("river_segments")
        .and_then(Value::as_array)
        .filter(|v| !v.is_empty())
        .ok_or("Invalid river segments or speeds")?;
    let speeds = rules
        .get("river_speeds")
        .filter(|v| v.is_object())
        .ok_or("Invalid river segments or speeds")?;
    let mut water_time = 0.0;
    let mut quoted = Vec::with_capacity(segments.len());
    for segment in segments {
        let downstream = segment
            .get("downstream_from")
            .ok_or("Invalid river segment flow")?;
        let flow = if downstream.is_null() {
            "still"
        } else {
            let downstream = downstream.as_str().ok_or("Invalid river segment flow")?;
            if downstream != string(route, "from")? && downstream != string(route, "to")? {
                return Err("Invalid river segment flow".into());
            }
            if source == downstream {
                "downstream"
            } else {
                "upstream"
            }
        };
        let table = if let Some(key) = segment.get("speed_key") {
            let key = key.as_str().ok_or("Invalid river speed table")?;
            speeds
                .get(key)
                .filter(|v| v.is_object())
                .ok_or("Invalid river speed table")?
        } else {
            speeds
        };
        let speed = river_number(table.get(flow), "Invalid river speed", false)?;
        let distance = river_number(
            segment.get("distance_km"),
            "Invalid river segment distance",
            false,
        )?;
        water_time += distance / speed;
        let mut item = normalized(segment)?;
        item["flow"] = json!(flow);
        item["speed_km_per_day"] = numeric(speed, true)?;
        quoted.push(item);
    }
    let zero = json!(0);
    let land = river_number(
        Some(route.get("land_km").unwrap_or(&zero)),
        "Invalid river land distance",
        true,
    )?;
    let one = json!(1);
    let embark = integer(
        rules.get("river_embark_days").unwrap_or(&one),
        "Invalid river embark days",
    )?;
    let same_flow = quoted.iter().all(|v| v["flow"] == quoted[0]["flow"]);
    let same_speed = quoted
        .iter()
        .all(|v| v["speed_km_per_day"] == quoted[0]["speed_km_per_day"]);
    leg["flow"] = if same_flow {
        quoted[0]["flow"].clone()
    } else {
        json!("mixed")
    };
    leg["speed_km_per_day"] = if same_speed {
        quoted[0]["speed_km_per_day"].clone()
    } else {
        Value::Null
    };
    leg["river_segments"] = json!(quoted);
    leg["land_access_days"] = numeric((land / plain).ceil(), true)?;
    leg["water_days"] = numeric(water_time.ceil(), true)?;
    leg["embark_days"] = json!(embark);
    leg["days"] = numeric(
        ((land / plain).ceil() + water_time.ceil() + embark as f64).max(1.0),
        true,
    )?;
    Ok(leg)
}

pub(crate) fn evaluate(
    data: &Value,
    route: &Value,
    source: &str,
    target: &str,
    departure_month: &Value,
) -> Result<Value> {
    let month = integer(
        departure_month,
        "Departure month must be an integer from1 to12",
    )?;
    if !(1..=12).contains(&month) {
        return Err("Departure month must be an integer from1 to12".into());
    }
    if !allowed(data, route, source, target)? {
        return Err("Route does not permit this direction".into());
    }
    let mut leg = normalized(route)?;
    if !leg.is_object() {
        return Err("route must be an object".into());
    }
    leg["from"] = json!(source);
    leg["to"] = json!(target);
    let policy = &data["travel_hazards"];
    let rules = field(data, "travel_rules")?;
    let plain = number(
        field(field(rules, "speeds")?, "plain")?,
        "Invalid plain speed",
    )?;
    if plain <= 0.0 {
        return Err("Invalid plain speed".into());
    }
    let distance = number(field(route, "distance_km")?, "Invalid route distance")?;
    let base_days = (distance / plain).ceil().max(1.0);
    leg["base_days"] = numeric(base_days, true)?;
    leg["hazard"] = Value::Null;
    match string(route, "mode")? {
        "land" => {
            let yinping = &policy["yinping"];
            if source == text(yinping, "from", "yinping")?
                && target == text(yinping, "to", "shujun")?
            {
                let (n, d) = ratio(
                    yinping.get("survival_numerator").unwrap_or(&json!(1)),
                    yinping.get("survival_denominator").unwrap_or(&json!(3)),
                )?;
                let multiplier = yinping.get("time_multiplier");
                leg["days"] = numeric(
                    base_days * num(yinping, "time_multiplier", 2.0)?,
                    multiplier.is_none_or(|v| v.as_number().is_some_and(|v| !v.is_f64())),
                )?;
                leg["hazard"] =
                    fixed("yinping", "阴平险道：全军最终余三分之一", n, d, month, None)?;
                return Ok(leg);
            }
            let ziwu = &policy["ziwu"];
            let start = text(ziwu, "from", "hanzhong")?;
            let end = text(ziwu, "to", "jingzhao")?;
            if ((source == start && target == end) || (source == end && target == start))
                && text(route, "special", "ziwu")? == "ziwu"
            {
                let rain = in_months(ziwu, "rain_months", month, &[7, 8, 9])?;
                let loss_name = if rain {
                    "rain_loss_percent"
                } else {
                    "dry_loss_percent"
                };
                let loss_value =
                    ziwu.get(loss_name)
                        .cloned()
                        .unwrap_or(json!(if rain { 50 } else { 20 }));
                let loss = integer(&loss_value, RATIO_ERROR)?;
                let n = 100_u64.checked_sub(loss).ok_or(RATIO_ERROR)?;
                let mult_name = if rain {
                    "rain_time_multiplier"
                } else {
                    "dry_time_multiplier"
                };
                let integral = ziwu
                    .get(mult_name)
                    .is_none_or(|v| v.as_number().is_some_and(|v| !v.is_f64()));
                leg["days"] = numeric(
                    base_days * num(ziwu, mult_name, if rain { 4.0 } else { 2.0 })?,
                    integral,
                )?;
                leg["hazard"] = fixed(
                    if rain { "ziwu_rain" } else { "ziwu_dry" },
                    if rain {
                        "子午谷暴雨：减员50%"
                    } else {
                        "子午谷险道：减员20%"
                    },
                    n,
                    100,
                    month,
                    Some(if rain { "rainy" } else { "dry" }),
                )?;
            }
        }
        "river" => return river(rules, route, leg, source, plain),
        "sea" => {
            let monsoon = &policy["monsoon"];
            let (season, label, vector) =
                if in_months(monsoon, "southwest_months", month, &[5, 6, 7, 8, 9])? {
                    ("southwest_monsoon", "西南季风", 1.0)
                } else if in_months(monsoon, "northeast_months", month, &[10, 11, 12, 1, 2, 3])? {
                    ("northeast_monsoon", "东北季风", -1.0)
                } else {
                    return Ok(leg);
                };
            let ((lon1, lat1), (lon2, lat2)) =
                (coordinates(data, source)?, coordinates(data, target)?);
            let east =
                (lon2 - lon1) * (((lat1 + lat2) / 2.0) * (std::f64::consts::PI / 180.0)).cos();
            let north = lat2 - lat1;
            let following = east * vector + north * vector > 0.0;
            let speed = if following {
                plain * num(monsoon, "tailwind_speed_multiplier", 4.0)?
            } else {
                plain / num(monsoon, "headwind_speed_divisor", 4.0)?
            };
            if speed <= 0.0 || !speed.is_finite() {
                return Err("Invalid monsoon speed".into());
            }
            let access_days = (num(route, "land_km", 0.0)? / plain).ceil();
            let water_days = (num(route, "sea_km", distance)? / speed).ceil();
            let embark = num(rules, "embark_days", 2.0)?;
            leg["days"] = numeric(
                (access_days + water_days + embark).max(1.0),
                rules
                    .get("embark_days")
                    .is_none_or(|v| v.as_number().is_some_and(|v| !v.is_f64())),
            )?;
            let range = monsoon
                .get("storm_loss_percent")
                .cloned()
                .unwrap_or(json!([80, 90]));
            let range = range
                .as_array()
                .filter(|v| v.len() == 2)
                .ok_or("Invalid storm loss range")?;
            let (low, high) = (
                integer(&range[0], "Invalid storm loss range")?,
                integer(&range[1], "Invalid storm loss range")?,
            );
            if low > high || high > 100 {
                return Err("Invalid storm loss range".into());
            }
            leg["hazard"] = json!({"kind":"monsoon_storm",
                "label":format!("{label}{}及暴风雨：全程减员{low}–{high}%", if following { "顺风" } else { "逆风" }),
                "season":season,"wind":if following { "tailwind" } else { "headwind" },"month":month,
                "loss_percent_min":low,"loss_percent_max":high,"loss_percent":null,
                "survival_numerator":null,"survival_denominator":null,"speed_km_per_day":numeric(speed, true)?});
        }
        _ => {}
    }
    Ok(leg)
}

pub(crate) fn survival_preview(request: &Value) -> Result<Value> {
    let troops = values(field(request, "troops")?)?;
    let routes = field(field(request, "quote")?, "routes")?
        .as_array()
        .ok_or("routes must be an array")?;
    let mut minimum = troops.clone();
    let mut maximum = troops;
    let mut storm = false;
    for route in routes {
        let Some(hazard) = route.get("hazard").filter(|v| truthy(Some(v))) else {
            continue;
        };
        let (min_n, max_n, d) = if string(hazard, "kind")? == "monsoon_storm" {
            if storm {
                continue;
            }
            storm = true;
            let low = integer(
                field(hazard, "loss_percent_min")?,
                "Invalid storm loss range",
            )?;
            let high = integer(
                field(hazard, "loss_percent_max")?,
                "Invalid storm loss range",
            )?;
            if low > high || high > 100 {
                return Err("Invalid storm loss range".into());
            }
            (100 - high, 100 - low, 100)
        } else {
            let (n, d) = ratio(
                field(hazard, "survival_numerator")?,
                field(hazard, "survival_denominator")?,
            )?;
            (n, n, d)
        };
        minimum = allocate(&minimum, min_n, d)?;
        maximum = allocate(&maximum, max_n, d)?;
    }
    Ok(json!({"minimum":minimum,"maximum":maximum}))
}
