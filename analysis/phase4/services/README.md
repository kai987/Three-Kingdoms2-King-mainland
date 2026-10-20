# 独立固定银行辅助服务

`runtime_services.py`执行本目录482条提升后IR，不读取原ROM控制指令；ROM仅提供只读表数据。29个有边界入口在[entries.json](entries.json)，逐条原字节在[services.asm](services.asm)。

14,848个实际6502对照全部通过，比较A/X/Y/P/SP/PC、完整RAM/SRAM、PRG物理银行和4015写请求，D标志按NES游戏保持清零。菜单使用有终止符的有限矩阵并覆盖方向组合/环绕，RNG supplied bound0会不终止，因此明确不测。动态访问478个原地址，静态482条逐字节验证另列。

输入ED1E/ED23/ED28是真正处理光标和数组，不是返回固定值。消息F26D/F283/F28B/F293/F29B真正写0310..0313及0300=0；调用者不能把它当文本已显示。E609及批量音序入口真正加载0700..0703和APU启用请求，未合成波形。F237/F24B/F25F/F266真正改变只读数据窗和记录原selector。

`PrgDataMemory`实现RAM镜像、SRAM、四个PRG窗，拒绝未知硬件访问。`GameEngine(mapped=True)`自动接入这些服务，剩余renderer/转属/跨银行调用仍明确报缺失。调用时保留原CPU协议，和只承诺游戏字段的duel_logic/postbattle API分层。

```sh
.venv-trace/bin/python scripts/analyze_runtime_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_runtime_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
