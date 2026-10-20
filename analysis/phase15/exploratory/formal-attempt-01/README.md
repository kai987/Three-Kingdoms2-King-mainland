# 第一次完整双跑：静态同帧QA未通过，不作为正式证据

四案原非空产物双跑均逐字节一致，但连续出征案 `second-battle-position-prepared`（frame10692）是在两byte坐标准备后、尚未执行新的原核心帧时保存。该PNG仍属于准备前实际帧，RAM已经是准备后数据，所以不能以这张图说明准备后的实际绘制。检查发现唯一此检查点与逐帧RAMhash不一致。

正式捕获已取消该尚无新帧的PNG，仅保留精确before/after完整RAM/SRAM准备dump，随后由真实普通按键执行的新帧截图可展示。正式数据在新 `analysis/phase15/runtime` 和 `runtime-repeat`，本目录及同名repeat仅保存探索/失败审计，不纳入正式通过计数。本次原JSON中旧runtime路径保持原样，没有裁剪或规范化state。
