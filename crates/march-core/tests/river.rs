use march_core::run;
use serde_json::{json, Value};

fn data() -> Value {
    json!({"travel_rules":{"speeds":{"plain":30,"sea":70},"river_embark_days":1,
        "river_speeds":{"yangtze":{"upstream":20,"downstream":50},
                        "xiang":{"upstream":22.5,"downstream":35}}},
        "travel_hazards":{"coastal_cities":[]},"exploration_routes":[],
        "city_coordinates":{"s":[114.3,30.5],"t":[112.9,28.2]},
        "travel_routes":[{"id":"s:t:river","from":"s","to":"t","mode":"river",
            "terrain":"river","distance_km":556,"land_km":31,"river_km":525,"days":28,
            "river_segments":[{"distance_km":300,"speed_key":"yangtze","downstream_from":"t"},
                              {"distance_km":225,"speed_key":"xiang","downstream_from":"t"}]},
            {"id":"s:t:land","from":"s","to":"t","mode":"land","terrain":"plain",
             "distance_km":600,"land_km":600,"days":20}]})
}

fn value(request: Value) -> Value {
    let result = run(&request);
    assert_eq!(result["ok"], true, "{result}");
    result["value"].clone()
}

#[test]
fn river_current_is_directional_and_never_seasonal_or_lossy() {
    let d = data();
    let raw = &d["travel_routes"][0];
    for month in 1..=12 {
        for (source, target, flow, days, speeds) in [
            ("s", "t", "upstream", 28, [20.0, 22.5]),
            ("t", "s", "downstream", 16, [50.0, 35.0]),
        ] {
            let q = value(json!({"op":"evaluate_leg","data":d,"route":raw,
                "source":source,"target":target,"month":month}));
            assert_eq!(q["days"], days);
            assert_eq!(q["flow"], flow);
            assert!(q["hazard"].is_null());
            assert!(q["speed_km_per_day"].is_null());
            assert_eq!(q["land_access_days"], 2);
            assert_eq!(q["embark_days"], 1);
            for (index, speed) in speeds.into_iter().enumerate() {
                assert_eq!(
                    q["river_segments"][index]["speed_km_per_day"].as_f64(),
                    Some(speed)
                );
            }
        }
    }
}

#[test]
fn river_mode_quotes_direct_water_while_land_stays_land() {
    let d = data();
    let cities = json!([{"id":"s","owner":"p"},{"id":"t","owner":"p"}]);
    let bulk = value(json!({"op":"batch","data":d,"cities":cities,"month":7,"player":"p"}));
    assert_eq!(bulk["s:t:river"]["days"], 28);
    assert_eq!(bulk["t:s:river"]["days"], 16);
    assert_eq!(bulk["s:t:fastest"]["modes"], json!(["land"]));
    assert_eq!(bulk["t:s:fastest"]["modes"], json!(["river"]));
    assert_eq!(bulk["t:s:land"]["modes"], json!(["land"]));
    assert!(bulk.get("s:t:sea").is_none());
    assert_eq!(
        value(json!({"op":"path","data":d,"cities":cities,"month":7,
        "owner":"p","source":"t","target":"s","mode":"river"})),
        bulk["t:s:river"]
    );
}

#[test]
fn river_rounds_aggregate_water_time_once_and_rejects_invalid_flow() {
    let d = data();
    let mut raw = d["travel_routes"][0].clone();
    raw["river_segments"][0]["distance_km"] = json!(1);
    raw["river_segments"][1]["distance_km"] = json!(1);
    let q = value(json!({"op":"evaluate_leg","data":d,"route":raw,
        "source":"s","target":"t","month":7}));
    assert_eq!(q["water_days"], 1);
    raw["river_segments"][0]["downstream_from"] = json!("missing");
    assert_eq!(
        run(&json!({"op":"evaluate_leg","data":d,"route":raw,
        "source":"s","target":"t","month":7}))["error"],
        "Invalid river segment flow"
    );
}
