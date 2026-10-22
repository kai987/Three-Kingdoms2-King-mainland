# March core

The same deterministic Rust library builds as a native `cdylib` for the Python
host and `wasm32-unknown-unknown` for the browser Worker. It calculates directed
routes, terrain travel times, seasonal wind, valley hazards, and proportional
integer survivors. It neither draws random numbers nor modifies a campaign.
The host still owns storm severity rolls, settlement order, saves, and checksums.

Every JSON request returns `{"ok":true,"value":...}` or
`{"ok":false,"error":"..."}`. Supported operations:

| Operation | Input | Value |
| --- | --- | --- |
| `register` | `data` immutable catalog configuration | Integer context handle |
| `unregister` | `context` | Whether the handle existed |
| `allowed` | `route`, `source`, `target` | Boolean |
| `evaluate_leg` | `route`, `source`, `target`, `month` | Directional route quote |
| `path` | `cities`, `source`, `target`, `owner`, `month`, optional `mode`, `adjacent`, `discovered` | Quote or `null` |
| `batch` | `cities`, `player`, `month`, optional `discovered` | Map of `source:target:mode` quotes |
| `allocate` | `troops`, `numerator`, `denominator` | Survivor counts in input order |
| `survival_preview` | `quote`, `troops` | `{minimum,maximum}` survivor arrays |

`allowed`, `evaluate_leg`, `path`, and `batch` accept either a registered
`context` or an inline `data` object. Configuration contains `travel_rules`,
`travel_hazards`, `city_coordinates`, `travel_routes`, `exploration_routes`, and
`links` (legacy attack adjacency). `cities` is an ordered array of `{id,owner}`.
The registry retains at most 512 contexts; callers release evicted configurations.
Handles are never silently reused or evicted.

Preview merges monsoon legs into one whole-voyage storm at its first occurrence,
then applies any fixed hazards in encounter order. Minimum survivors use maximum
storm loss, maximum survivors use minimum storm loss. This never selects a roll.

Scalar direct routes break equal time/distance ties by route ID. Batch direct
quotes retain catalog insertion order, matching the existing host behavior.
Route trees use `(days,distance,city,serial)` ordering. Legacy raw route metadata,
orientation, and float spellings remain intact; hazard quotes normalize integral
numbers for the existing browser/save checksum contract.

Friendly transfers require an owned destination, and may transit any number of
connected owned or `neutral` cities. Enemy cities block that route tree. Batch
searches expand neutral transit nodes without exposing them as remote attack
destinations: attack quotes remain direct legs from the source. Direct sea,
special, and exploration modes retain their existing one-leg restrictions.
The host rechecks transit ownership on arrival; the pure core has no occupation,
resource, random-number, or save side effects.

## ABI

Exports are `memory` (WASM), `march_version() -> 1`, `march_alloc(len) -> ptr`,
`march_call(ptr,len) -> result_ptr`, `march_result_len() -> len`, and
`march_free(ptr,len)`. Lengths are unsigned 32-bit integers. Native pointer types
must retain the platform pointer width; do not pack pointers into 32 bits.

Allocate an input, copy UTF-8 JSON into it, call the core, read result length and
bytes, then free both output and input with their original lengths. `march_call`
borrows the input. Only ABI-owned unfreed buffers with exact lengths may be freed.
Serialize the entire call/result-length/free sequence because the last result
length is shared. No NUL terminators are required. Individual requests are limited
to 64 MiB. Context access is mutex protected on the native host.

## Local checks

```sh
cargo test --manifest-path crates/march-core/Cargo.toml --locked
cargo clippy --manifest-path crates/march-core/Cargo.toml --all-targets --locked -- -D warnings
cargo build --manifest-path crates/march-core/Cargo.toml --release --locked
cargo build --manifest-path crates/march-core/Cargo.toml --release --locked --lib --target wasm32-unknown-unknown
```

The `march-core-json` binary accepts one request per input line and emits one
response per output line, making the native library usable in differential tests.
