# Current marching reference fixtures

`march-python-baseline.json` records the current `tk2-campaign-v1` campaign
(`game/data/campaigns/217-07.json`) with 99 officers per city. Its reproducer is
`campaign_result` in `tests/test_remake_march_core.py`, run under the explicit
`python` backend. These fixtures cover plain travel, Yinping, rainy/dry Ziwu,
three sea seasons/directions, and exploration. Controlled friendly destinations
isolate transport settlement; these are not unattended historical campaigns.

Each fixture records canonical SHA256 values for full state and exported saves,
RNG state/draws, soldier conservation, the physical route quote, and final troop
counts at before/preview/queued/arrived checkpoints. Python, native Rust and real
browser WASM must agree, and native/Python must load one another's pending-march
saves without rewriting checksums.

The fixtures were refreshed when archived scenarios and their save support were
removed: current catalog IDs, schema and full roster necessarily change full-save
hashes. The retained eight route quotes were checked against the earlier Python
reference; all physical quotes and storm RNG draws remained identical. Separately,
all 25 scenario openings and one-month calendar states, plus three natural AI
months and their RNG states, were checked byte-for-byte across the runtime cleanup.
Do not refresh these fixtures to accommodate a changed physical rule, RNG draw or
number spelling.
