//! Pure marching calculations shared by the Python host and browser Worker.
//!
//! The JSON protocol has no RNG, campaign mutation, or save serialization.
//! Callers own every allocated ABI buffer and must serialize the complete
//! call/result-length/free sequence. Pass only buffers from `march_alloc` to
//! `march_call` and `march_free`, with their original lengths.

mod hazards;
mod paths;

use serde_json::{json, Number, Value};
use std::collections::BTreeMap;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::{Arc, Mutex, OnceLock};

type Result<T> = std::result::Result<T, String>;
const MAX_CONTEXTS: usize = 512;
const MAX_BUFFER: usize = 64 * 1024 * 1024;

#[derive(Default)]
struct Registry {
    next: u32,
    data: BTreeMap<u32, Arc<Value>>,
}

fn registry() -> &'static Mutex<Registry> {
    static REGISTRY: OnceLock<Mutex<Registry>> = OnceLock::new();
    REGISTRY.get_or_init(|| Mutex::new(Registry::default()))
}

fn context(request: &Value) -> Result<Arc<Value>> {
    if let Some(data) = request.get("data") {
        if !data.is_object() {
            return Err("data must be an object".into());
        }
        return Ok(Arc::new(data.clone()));
    }
    let id = integer(field(request, "context")?, "Invalid context")?;
    let id = u32::try_from(id).map_err(|_| "Unknown march context")?;
    registry()
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .data
        .get(&id)
        .cloned()
        .ok_or_else(|| "Unknown march context".into())
}

pub(crate) fn field<'a>(value: &'a Value, name: &str) -> Result<&'a Value> {
    value
        .get(name)
        .ok_or_else(|| format!("Missing field: {name}"))
}

pub(crate) fn string<'a>(value: &'a Value, name: &str) -> Result<&'a str> {
    field(value, name)?
        .as_str()
        .ok_or_else(|| format!("{name} must be a string"))
}

pub(crate) fn number(value: &Value, error: &str) -> Result<f64> {
    value
        .as_f64()
        .filter(|v| v.is_finite())
        .ok_or_else(|| error.into())
}

pub(crate) fn integer(value: &Value, error: &str) -> Result<u64> {
    // as_u64 deliberately rejects a JSON floating-point spelling such as 1.0.
    if !value.as_number().is_some_and(|v| v.is_u64()) {
        return Err(error.into());
    }
    value.as_u64().ok_or_else(|| error.into())
}

pub(crate) fn numeric(value: f64, integral: bool) -> Result<Value> {
    if !value.is_finite() {
        return Err("Calculation produced a non-finite number".into());
    }
    if integral && value.fract() == 0.0 {
        if value >= 0.0 && value < u64::MAX as f64 {
            return Ok(Value::from(value as u64));
        }
        if value >= i64::MIN as f64 && value < i64::MAX as f64 {
            return Ok(Value::from(value as i64));
        }
    }
    Number::from_f64(value)
        .map(Value::Number)
        .ok_or_else(|| "Calculation produced a non-finite number".into())
}

pub(crate) fn normalized(value: &Value) -> Result<Value> {
    match value {
        Value::Array(items) => items
            .iter()
            .map(normalized)
            .collect::<Result<Vec<_>>>()
            .map(Value::Array),
        Value::Object(items) => items
            .iter()
            .map(|(k, v)| Ok((k.clone(), normalized(v)?)))
            .collect::<Result<serde_json::Map<_, _>>>()
            .map(Value::Object),
        Value::Number(n) if n.is_f64() => numeric(number(value, "Invalid route number")?, true),
        _ => Ok(value.clone()),
    }
}

pub(crate) fn truthy(value: Option<&Value>) -> bool {
    match value {
        None | Some(Value::Null) => false,
        Some(Value::Bool(v)) => *v,
        Some(Value::Object(v)) => !v.is_empty(),
        Some(Value::Array(v)) => !v.is_empty(),
        Some(Value::String(v)) => !v.is_empty(),
        Some(Value::Number(v)) => v.as_f64().is_some_and(|n| n != 0.0),
    }
}

fn execute(request: &Value) -> Result<Value> {
    match string(request, "op")? {
        "register" => {
            let data = field(request, "data")?;
            if !data.is_object() {
                return Err("data must be an object".into());
            }
            let mut registry = registry().lock().unwrap_or_else(|e| e.into_inner());
            if registry.data.len() >= MAX_CONTEXTS {
                return Err("March context registry is full".into());
            }
            registry.next = registry
                .next
                .checked_add(1)
                .ok_or("March context IDs exhausted")?;
            let id = registry.next;
            registry.data.insert(id, Arc::new(data.clone()));
            Ok(json!(id))
        }
        "unregister" => {
            let id = integer(field(request, "context")?, "Invalid context")?;
            let Ok(id) = u32::try_from(id) else {
                return Ok(json!(false));
            };
            Ok(json!(registry()
                .lock()
                .unwrap_or_else(|e| e.into_inner())
                .data
                .remove(&id)
                .is_some()))
        }
        "allowed" | "route_allowed" => {
            let data = context(request)?;
            Ok(json!(hazards::allowed(
                &data,
                field(request, "route")?,
                string(request, "source")?,
                string(request, "target")?
            )?))
        }
        "evaluate_leg" => {
            let data = context(request)?;
            hazards::evaluate(
                &data,
                field(request, "route")?,
                string(request, "source")?,
                string(request, "target")?,
                field(request, "month")?,
            )
        }
        "path" => paths::path(context(request)?.as_ref(), request),
        "batch" => paths::batch(context(request)?.as_ref(), request),
        "allocate" => hazards::allocate_request(request),
        "survival_preview" => hazards::survival_preview(request),
        _ => Err("Unknown march operation".into()),
    }
}

/// Execute one parsed request, returning the stable JSON success/error envelope.
pub fn run(request: &Value) -> Value {
    match execute(request) {
        Ok(value) => json!({"ok": true, "value": value}),
        Err(error) => json!({"ok": false, "error": error}),
    }
}

/// Execute one UTF-8 JSON request. Malformed requests are protocol errors.
pub fn run_json(bytes: &[u8]) -> Vec<u8> {
    let result = match serde_json::from_slice::<Value>(bytes) {
        Ok(request) => std::panic::catch_unwind(|| run(&request))
            .unwrap_or_else(|_| json!({"ok":false,"error":"March calculation failed"})),
        Err(error) => json!({"ok":false,"error":format!("Invalid JSON: {error}")}),
    };
    serde_json::to_vec(&result)
        .unwrap_or_else(|_| b"{\"ok\":false,\"error\":\"JSON encoding failed\"}".to_vec())
}

static RESULT_LEN: AtomicU32 = AtomicU32::new(0);

#[no_mangle]
pub extern "C" fn march_version() -> u32 {
    1
}

#[no_mangle]
pub extern "C" fn march_result_len() -> u32 {
    RESULT_LEN.load(Ordering::SeqCst)
}

#[no_mangle]
pub extern "C" fn march_alloc(len: u32) -> *mut u8 {
    if len as usize > MAX_BUFFER {
        return std::ptr::null_mut();
    }
    Box::into_raw(vec![0_u8; len as usize].into_boxed_slice()) as *mut u8
}

/// # Safety
/// `ptr` must address `len` bytes owned by the caller and remain valid during this call.
#[no_mangle]
pub unsafe extern "C" fn march_call(ptr: *const u8, len: u32) -> *mut u8 {
    let output = if ptr.is_null() || len as usize > MAX_BUFFER {
        b"{\"ok\":false,\"error\":\"Invalid request buffer\"}".to_vec()
    } else {
        run_json(std::slice::from_raw_parts(ptr, len as usize))
    };
    RESULT_LEN.store(output.len() as u32, Ordering::SeqCst);
    Box::into_raw(output.into_boxed_slice()) as *mut u8
}

/// # Safety
/// `ptr` and `len` must be an unfreed allocation returned by this ABI.
#[no_mangle]
pub unsafe extern "C" fn march_free(ptr: *mut u8, len: u32) {
    if !ptr.is_null() {
        drop(Box::from_raw(std::ptr::slice_from_raw_parts_mut(
            ptr,
            len as usize,
        )));
    }
}
