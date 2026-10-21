# Marching compatibility fixtures

`march-python-baseline.json` was captured from the Python implementation at
commit `805abd6a3f84583846a5804a23f9bfa229a19941`, before introducing Rust dispatch.
The reproducer is `campaign_result` in `tests/test_remake_march_core.py`.

It records canonical SHA256 values for full state and exported version1 saves,
RNG state/draws and soldier conservation at before/preview/queued/arrived
checkpoints. The nine scenarios cover plain travel, Yinping, rainy/dry Ziwu,
three sea seasons/directions, exploration and a released legacy catalog.
Controlled friendly destinations isolate transport settlement; these fixtures
do not represent unattended historical campaigns. Both backends must reproduce
them and load one another's pending-march saves without rewriting checksums.

Do not refresh the fixtures to accommodate a changed rule or number spelling.
