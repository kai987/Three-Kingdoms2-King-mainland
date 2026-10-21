use march_core::{
    march_alloc, march_call, march_free, march_result_len, march_version, run, run_json,
};
use serde_json::{json, Value};

fn data() -> Value {
    json!({"travel_rules":{"speeds":{"plain":30,"sea":70},"embark_days":2},
        "travel_hazards":{"schema":"test","coastal_cities":["a","b","c"]},
        "city_coordinates":{"a":[110,20],"b":[120,30],"c":[125,35]},
        "travel_routes":[],"exploration_routes":[]})
}

fn land(a: &str, b: &str, km: f64) -> Value {
    json!({"id":format!("{a}:{b}:land"),"from":a,"to":b,"mode":"land",
        "terrain":"mountain","distance_km":km,"land_km":km,"sea_km":0,"days":20})
}

fn value(request: Value) -> Value {
    let result = run(&request);
    assert_eq!(result["ok"], true, "{result}");
    result["value"].clone()
}

#[test]
fn proportional_survivors_conserve_whole_army_and_input_order() {
    for troops in [
        vec![],
        vec![0],
        vec![1, 1, 1],
        vec![0, 1, 2, 999, 1000],
        vec![999; 30],
    ] {
        for (n, d) in [(0, 1), (1, 1), (1, 3), (1, 2), (1, 10), (4, 5)] {
            let result =
                value(json!({"op":"allocate","troops":troops,"numerator":n,"denominator":d}));
            let result: Vec<u64> = serde_json::from_value(result).unwrap();
            assert_eq!(
                result.iter().sum::<u64>(),
                troops.iter().sum::<u64>() * n / d
            );
            assert!(result.iter().zip(&troops).all(|(a, b)| a <= b));
        }
    }
    assert_eq!(
        value(json!({"op":"allocate","troops":[1,1,1],"numerator":1,"denominator":3})),
        json!([1, 0, 0])
    );
    assert_eq!(
        value(json!({"op":"allocate","troops":[1,2],"numerator":1,"denominator":3})),
        json!([0, 1])
    );
    assert_eq!(
        value(json!({"op":"allocate","troops":[u64::MAX],"numerator":1,"denominator":3})),
        json!([u64::MAX / 3])
    );
}

#[test]
fn invalid_ratio_and_troops_reject_float_and_boolean_spellings() {
    for (n, d) in [
        (json!(-1), json!(3)),
        (json!(4), json!(3)),
        (json!(1), json!(0)),
        (json!(true), json!(3)),
        (json!(1), json!(1.0)),
    ] {
        let result = run(&json!({"op":"allocate","troops":[],"numerator":n,"denominator":d}));
        assert_eq!(
            result["error"],
            "Survival ratio must be integers with0<=n<=d andd>0"
        );
    }
    for troops in [json!([-1]), json!([true]), json!([1.5])] {
        assert_eq!(
            run(&json!({"op":"allocate","troops":troops,"numerator":1,"denominator":3}))["error"],
            "Troop counts must be nonnegative integers"
        );
    }
}

#[test]
fn yinping_direction_and_ziwu_season_use_plain_baseline() {
    let yinping = land("yinping", "shujun", 300.0);
    assert_eq!(
        value(
            json!({"op":"allowed","data":data(),"route":yinping,"source":"shujun","target":"yinping"})
        ),
        false
    );
    let q = value(
        json!({"op":"evaluate_leg","data":data(),"route":yinping,"source":"yinping","target":"shujun","month":7}),
    );
    assert_eq!(q["days"], 20);
    assert_eq!(q["base_days"], 10);
    assert_eq!(q["hazard"]["survival_denominator"], 3);
    for month in 1..=12 {
        let q = value(
            json!({"op":"evaluate_leg","data":data(),"route":land("hanzhong","jingzhao",300.0),"source":"jingzhao","target":"hanzhong","month":month}),
        );
        assert_eq!(q["days"], if (7..=9).contains(&month) { 40 } else { 20 });
    }
    for month in [json!(0), json!(13), json!(true), json!(1.0)] {
        assert_eq!(
            run(
                &json!({"op":"evaluate_leg","data":data(),"route":yinping,"source":"yinping","target":"shujun","month":month})
            )["error"],
            "Departure month must be an integer from1 to12"
        );
    }
}

#[test]
fn sea_wind_reverses_with_direction_and_month_but_april_is_unchanged() {
    let route = json!({"id":"sea","from":"a","to":"b","mode":"sea","distance_km":1231,"land_km":31,"sea_km":1200,"days":22});
    for (source, target, month, days, wind) in [
        ("a", "b", 7, 14, "tailwind"),
        ("b", "a", 7, 164, "headwind"),
        ("b", "a", 1, 14, "tailwind"),
    ] {
        let q = value(
            json!({"op":"evaluate_leg","data":data(),"route":route,"source":source,"target":target,"month":month}),
        );
        assert_eq!(q["days"], days);
        assert_eq!(q["hazard"]["wind"], wind);
        assert!(q["hazard"]["loss_percent"].is_null());
    }
    assert_eq!(
        value(
            json!({"op":"evaluate_leg","data":data(),"route":route,"source":"a","target":"b","month":4})
        )["days"],
        22
    );
    let mut flat = data();
    flat["city_coordinates"]["b"] = flat["city_coordinates"]["a"].clone();
    assert_eq!(
        value(
            json!({"op":"evaluate_leg","data":flat,"route":route,"source":"a","target":"b","month":7})
        )["hazard"]["wind"],
        "headwind"
    );
}

#[test]
fn legacy_keeps_reverse_raw_metadata_and_float_number_spelling() {
    let mut legacy = data();
    legacy["travel_hazards"] = json!({});
    let route = land("a", "b", 300.0);
    let q = value(
        json!({"op":"evaluate_leg","data":legacy,"route":route,"source":"b","target":"a","month":4}),
    );
    assert_eq!(q, route);
    assert!(q["distance_km"].as_number().unwrap().is_f64());
    assert_eq!(q["from"], "a");
    legacy["travel_routes"] = json!([route]);
    let q = value(
        json!({"op":"path","data":legacy,"cities":[{"id":"a","owner":"p"},{"id":"b","owner":"p"}],"month":4,"source":"b","target":"a","owner":"p"}),
    );
    assert!(q["distance_km"].as_number().unwrap().is_f64());
    assert_eq!(q["routes"][0]["from"], "a");
}

#[test]
fn scalar_direct_ties_use_id_while_batch_ties_preserve_route_order() {
    let mut d = data();
    let mut first = land("a", "b", 2.25);
    first["mode"] = json!("sea");
    first["id"] = json!("z");
    let mut second = first.clone();
    second["id"] = json!("a");
    d["travel_routes"] = json!([first, second]);
    let cities = json!([{"id":"a","owner":"p"},{"id":"b","owner":"p"}]);
    let scalar = value(
        json!({"op":"path","data":d,"cities":cities,"month":4,"source":"a","target":"b","owner":"p","mode":"sea"}),
    );
    assert_eq!(scalar["routes"][0]["id"], "a");
    let bulk = value(json!({"op":"batch","data":d,"cities":cities,"month":4,"player":"p"}));
    assert_eq!(bulk["a:b:sea"]["routes"][0]["id"], "z");
    assert_eq!(bulk["a:b:sea"]["distance_km"], 2.2);
}

#[test]
fn survival_preview_merges_sea_storm_once_in_first_occurrence_order() {
    let storm =
        json!({"hazard":{"kind":"monsoon_storm","loss_percent_min":80,"loss_percent_max":90}});
    let fixed =
        json!({"hazard":{"kind":"yinping","survival_numerator":1,"survival_denominator":3}});
    let result = value(
        json!({"op":"survival_preview","troops":[1000,1000,1000],"quote":{"routes":[storm,fixed,storm]}}),
    );
    assert_eq!(result, json!({"minimum":[34,33,33],"maximum":[67,67,66]}));
}

#[test]
fn registry_handles_are_released_without_aliasing_a_new_context() {
    let handle = value(json!({"op":"register","data":data()}));
    assert_eq!(value(json!({"op":"unregister","context":handle})), true);
    assert_eq!(value(json!({"op":"unregister","context":handle})), false);
    assert_eq!(
        run(
            &json!({"op":"allowed","context":handle,"route":land("a","b",3.0),"source":"a","target":"b"})
        )["error"],
        "Unknown march context"
    );
    let next = value(json!({"op":"register","data":data()}));
    assert_ne!(next, handle);
    value(json!({"op":"unregister","context":next}));
}

#[test]
fn malformed_json_and_incomplete_protocol_return_errors_without_panics() {
    for bytes in [
        b"{".as_slice(),
        b"null",
        b"[]",
        b"{}",
        b"{\"op\":\"allocate\"}",
        b"{\"op\":\"path\",\"data\":{}}",
    ] {
        let result: Value = serde_json::from_slice(&run_json(bytes)).unwrap();
        assert_eq!(result["ok"], false);
        assert!(result["error"].is_string());
    }
    for mode in [
        json!(null),
        json!(false),
        json!(1),
        json!([]),
        json!("invalid"),
    ] {
        assert_eq!(
            run(&json!({"op":"path","data":data(),"mode":mode}))["error"],
            "请选择有效的行军路线。"
        );
    }
}

#[test]
fn raw_abi_owns_separate_buffers_and_preserves_version() {
    let request = br#"{"op":"allocate","troops":[1,1,1],"numerator":1,"denominator":3}"#;
    assert_eq!(march_version(), 1);
    for _ in 0..32 {
        let input = march_alloc(request.len() as u32);
        assert!(!input.is_null());
        unsafe {
            std::ptr::copy_nonoverlapping(request.as_ptr(), input, request.len());
            let output = march_call(input, request.len() as u32);
            let len = march_result_len();
            let result: Value =
                serde_json::from_slice(std::slice::from_raw_parts(output, len as usize)).unwrap();
            assert_eq!(result["value"], json!([1, 0, 0]));
            march_free(output, len);
            // The input is borrowed by march_call and still belongs to us.
            assert_eq!(std::slice::from_raw_parts(input, request.len()), request);
            march_free(input, request.len() as u32);
        }
    }
}
