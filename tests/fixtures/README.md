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

The AI/event update adds `difficulty`, `ai_strategy` and bounded structured
`events` in the current campaign extension. Full-state/save hashes were refreshed
only after all32 checkpoints, with precisely these three new fields projected
out and the envelope checksum recomputed, matched the previous full-state and
full-save hashes exactly. All8 physical route quotes, final troops, dates,
soldier ledgers and RNG states/draws also matched the prior fixtures unchanged.
The current fixtures continue to pin the complete new state and save, including
new event records; the tests do not project away those fields during acceptance.

Faction-wide administration uses `tk2-domestic-v2`: a single pair of offices and
policy per faction, with separate city training/income receipts. The UI entry also
refreshes the pinned route-source fingerprint and catalog identity. All32 current
checkpoints were regenerated under the Python backend only after proving that
every field except full-state/save hashes matched the preceding fixtures: route
quotes, dates, final troops, soldier ledgers, and RNG state/draws are unchanged.

## 捨命一擊接入前的單挑向量

`duel-pre-desperate-baseline.json`由凍結的`eea539c`程式擷取，記錄8個種子×4種既有招式的完整狀態雜湊、亂數與回執。兩方體力80，避免觸發新增的低體力AI捨命選擇；新招式沒有被任何一方選中時，這些既有操作應保持逐項一致。

單挑動作擴充提交另因 `app.js` 指紋更新重綁32個行軍存檔包雜湊；重建前逐項確認八條行軍案例的完整狀態、RNG、路線報價、存活兵數及回合完全不變。此項不更新任何行軍公式或狀態雜湊。
