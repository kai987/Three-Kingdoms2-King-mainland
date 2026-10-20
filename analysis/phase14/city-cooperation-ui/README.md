# 城市合作 AI 的真实标记与文字请求

新增独立[CityCooperationUIServices](../../../source/recovered/city_cooperation_ui_services.py)，补齐 physical29/30 `A042 → AA37` 及本地 `AB38`。原闭包148条指令，两个固定调用 `AB3A → F25F`、`AB50 → EBE9` 复用已有独立源码，保留实际JSR栈、scratch和mapper协议。运行时不执行ROM、IR或opcode，也没有原CPUfallback。

`0A` 是四组标题编号0..3或FF空标题，`0B` 是标记记录ID（FF跳过），`0C` 非零时只绘制标记。AB38选择NMI数据窗E1/E000=49，即physical17；按13×rawID读取13字节记录，首字节写CHR页B9，其余至多12字节建立OAM。原FF提前终止、空列中心偏移、tile+C0及OAM7C的byte溢出均保留。直接237..255测试是字节寻址边界，不声称有效武将身份。

AA37保存并恢复0A/0B/0C。标题路径产生0380中的两行tile请求，写7E|4；它不消费PPU任务、不确认继承人、不写6F8B=1。真正城市NMI2从25/26 C7E0（C835等selector3D调用）使用此服务；后续等待/计时与主循环resume在上层整合回执单列。

正式原CPU对照 **1264次完整callerRTS、5个源码拒绝测试、0失败**，全部2048B RAM（含inactive栈）、8192B SRAM、AXYP/SP/PC、银行、读口与有序写口比较。原148条body中动态覆盖148条；全256raw记录、256个原callerSP及256个OAMbyte cursor是有界服务输入，不代表自然核心逐一触发。测试不导入人为ready或结果标志。

```python
service = CityCooperationUIServices(memory, rom, services=None)
service.run_entry(0xA042, registers=actual_caller_registers)
service(ServiceCall(...))  # exact29/30 ownership; existingcallerframe
```

```sh
.venv-trace/bin/python scripts/verify_city_cooperation_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_cooperation_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[验证](validation.json) · [原始汇编](original.asm) · [字节和表](static-catalog.json) · [哈希证据](evidence.json)
