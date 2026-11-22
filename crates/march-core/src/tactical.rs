//! Read-only tactical forecasts. Unit indices refer to the caller's ordered
//! rosters; resolving an actual movement or attack remains a campaign command.
use crate::Result;
use serde::Deserialize;
use serde_json::{json, Value};
use std::cmp::Reverse;
use std::collections::BinaryHeap;

const MAX_BATTLE_OFFICERS: usize = 20;

#[derive(Deserialize)]
struct Unit {
    troops: i64,
    martial: i64,
    morale: i64,
    spirit: i64,
    guarded: bool,
    stunned: bool,
    cell: Option<usize>,
    costs: Option<[usize; 6]>,
    #[serde(default)]
    sites: Vec<Site>,
}

#[derive(Deserialize)]
struct Site {
    cell: usize,
    score: f64,
}

#[derive(Deserialize)]
struct Board {
    width: usize,
    tiles: Vec<u8>,
    camp: Option<usize>,
    points: usize,
    contact: bool,
}

#[derive(Deserialize)]
struct Request {
    friends: Vec<Unit>,
    enemies: Vec<Unit>,
    enemy_rank: Vec<usize>,
    damage_percent: i64,
    board: Option<Board>,
}

fn damage(a: &Unit, troops: i64, b: &Unit, percent: i64) -> f64 {
    let base = troops * (a.martial + 40) * percent;
    let denominator = (b.martial + 80) * 10000;
    let factor = (100 + (a.morale - 70).div_euclid(3)).clamp(80, 110);
    let mut sum = 0;
    for spread in 90..=110 {
        let hit = (base * spread / denominator).max(1);
        let hit = (hit * factor * a.spirit / 10000).clamp(1, b.troops);
        sum += if b.guarded { (hit / 2).max(1) } else { hit };
    }
    sum as f64 / 21.
}

fn loss(unit: &Unit, damage: f64) -> f64 {
    damage.min(unit.troops as f64)
        + if damage >= unit.troops as f64 {
            24.
        } else {
            0.
        }
}

fn neighbors(cell: usize, width: usize, size: usize) -> impl Iterator<Item = usize> {
    [
        cell.checked_sub(width),
        cell.checked_sub(1).filter(|_| !cell.is_multiple_of(width)),
        (cell % width + 1 < width).then_some(cell + 1),
        (cell + width < size).then_some(cell + width),
    ]
    .into_iter()
    .flatten()
}

fn movement(
    board: &Board,
    occupied: &[bool],
    actor: &Unit,
    enemies: &[Unit],
    ranks: &[usize],
    outgoing: &[f64],
) -> Vec<Value> {
    let mut rows = Vec::new();
    let (Some(source), Some(costs)) = (actor.cell, actor.costs) else {
        return rows;
    };
    let mut distance = vec![usize::MAX; occupied.len()];
    let mut previous = vec![source; occupied.len()];
    distance[source] = 0;
    let mut queue = BinaryHeap::from([Reverse((0, source))]);
    while let Some(Reverse((cost, here))) = queue.pop() {
        if distance[here] != cost || (Some(here) == board.camp && here != source) {
            continue;
        }
        for next in neighbors(here, board.width, occupied.len()) {
            if occupied[next] {
                continue;
            }
            let proposed = cost + costs[board.tiles[next] as usize];
            if proposed < distance[next] {
                distance[next] = proposed;
                previous[next] = here;
                queue.push(Reverse((proposed, next)));
            }
        }
    }
    let affordable = |mut goal: usize| {
        if distance[goal] == usize::MAX {
            return None;
        }
        while distance[goal] > board.points {
            goal = previous[goal]
        }
        (goal != source).then_some(goal)
    };
    let candidate = |cell: usize, target: usize, score: f64| {
        json!({
        "kind":"move","x":cell%board.width,"y":cell/board.width,"cost":distance[cell],
        "target":target,"score":score,"tactic":null})
    };
    if let Some(camp) = board
        .camp
        .filter(|&c| c != source && distance[c] <= board.points)
    {
        let mut row = candidate(camp, 0, 100000.);
        row["capture"] = Value::Bool(true);
        rows.push(row);
    }
    for (index, site) in actor.sites.iter().enumerate() {
        if let Some(cell) = affordable(site.cell) {
            let mut row = candidate(
                cell,
                0,
                (site.score - distance[site.cell] as f64 * 0.25).max(1.),
            );
            row["site"] = index.into();
            rows.push(row);
        }
    }
    // Row-major cell index breaks ties in (y,x) order, as does the heap.
    let mut best = None;
    for (index, enemy) in enemies.iter().enumerate() {
        for dest in neighbors(enemy.cell.unwrap(), board.width, occupied.len()) {
            if distance[dest] != usize::MAX {
                let key = (distance[dest], ranks[index], dest, index);
                if best.is_none_or(|old| key < old) {
                    best = Some(key)
                }
            }
        }
    }
    if let Some((_, _, dest, index)) = best {
        if let Some(cell) = affordable(dest) {
            rows.push(candidate(
                cell,
                index,
                outgoing[index] * 0.4 + distance[cell] as f64 * 0.1,
            ));
        }
    }
    rows
}

pub(crate) fn candidates(request: &Value) -> Result<Value> {
    let r = Request::deserialize(request).map_err(|e| e.to_string())?;
    let units = r.friends.iter().chain(&r.enemies);
    // Conversions move existing officers across sides after deployment.
    if r.friends.len() + r.enemies.len() > MAX_BATTLE_OFFICERS
        || r.enemy_rank.len() != r.enemies.len()
        || !(0..=1000).contains(&r.damage_percent)
        || units.clone().any(|u| {
            !(1..=10000).contains(&u.troops)
                || !(0..=255).contains(&u.martial)
                || !(0..=100).contains(&u.morale)
                || !(0..=100).contains(&u.spirit)
        })
    {
        return Err("Invalid tactical units".into());
    }
    let mut occupied = Vec::new();
    if let Some(b) = &r.board {
        let size = b.tiles.len();
        if b.width == 0
            || size == 0
            || size > 4096
            || !size.is_multiple_of(b.width)
            || b.tiles.iter().any(|&v| v >= 6)
            || b.camp.is_some_and(|c| c >= size)
        {
            return Err("Invalid tactical field".into());
        }
        occupied.resize(size, false);
        for unit in units {
            let cell = unit
                .cell
                .filter(|&n| n < size)
                .ok_or("Invalid tactical position")?;
            if unit.sites.iter().any(|s| s.cell >= size)
                || unit
                    .costs
                    .is_some_and(|costs| costs.iter().any(|v| !(1..=255).contains(v)))
            {
                return Err("Invalid tactical movement".into());
            }
            occupied[cell] = true;
        }
    }
    let mut result = Vec::new();
    for a in &r.friends {
        let mut outgoing = Vec::new();
        let mut incoming = Vec::new();
        let mut attacks = Vec::new();
        for b in &r.enemies {
            let hit = damage(a, a.troops, b, r.damage_percent);
            outgoing.push(hit);
            incoming.push(damage(b, b.troops, a, r.damage_percent));
            let legal = r.board.as_ref().is_none_or(|board| {
                board.contact
                    && neighbors(a.cell.unwrap(), board.width, board.tiles.len())
                        .any(|c| Some(c) == b.cell)
            });
            let score = if !legal {
                None
            } else if a.stunned {
                Some(0.)
            } else {
                let remaining = b.troops - hit as i64;
                let reply = if r.board.is_some() && !b.stunned && remaining > 0 {
                    damage(b, remaining, a, r.damage_percent)
                } else {
                    0.
                };
                Some(loss(b, hit) - loss(a, reply))
            };
            attacks.push(score);
        }
        let moves = r
            .board
            .as_ref()
            .filter(|_| !r.enemies.is_empty())
            .map(|b| movement(b, &occupied, a, &r.enemies, &r.enemy_rank, &outgoing))
            .unwrap_or_default();
        result.push(json!({"out":outgoing,"incoming":incoming,"attacks":attacks,"moves":moves}));
    }
    Ok(Value::Array(result))
}
