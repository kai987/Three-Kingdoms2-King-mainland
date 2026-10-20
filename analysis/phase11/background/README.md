# 阶段11：战场背景初建与原参数精灵入口

`BattleBackgroundInitialization` 独立恢复 physical23 `$A009 → A2FF` 的完整有界背景初建，以及 fixed31 `$F09C` 的原调用参数精灵入口。生产源码为直接整数运算、循环和具名函数；不执行原 ROM、不解释 IR、不调用原 CPU fallback。复用的滚屏、单位字形与固定 PPU 消费者也是已经独立恢复的源码。它不是原始游戏源码或完整 NES 仿真器。

## 完整背景调用

原代码将四个相机字节 `$008E..0091` 压到真实栈，临时增加 Y 高字节。计数器以30开始，每次递减后以 BPL 判断，因此构造的是 **31组 tile/attribute 行**，不能把“30行屏幕”当作30次循环。每组从真实直接入口 `$A485`、`$AD9F` 构造请求，再调用 fixed `$EEE6`；`$A324` 读取 `$007E` 并回到 `$A321`，直到全部原请求实际清除。

tile行构造17个 metatile，请求缓冲 `$0164`、bit `$40`；attribute行构造8或9个属性，请求缓冲 `$019C`、bit `$10`。这两个直接入口不同于滚屏外层 `$A387/$AB53` 的方向选择。源码没有临时篡改 `$009C` 来借用另一个路径。`$AE58` 的两条 cachebit分支原来执行相同合并，因此保留相同结果。unit覆盖保留最低slot优先、原packed row15缺口、原数据bank切换和边缘合并。

行间 Y 低字节减8；借位时再减16并减高字节，保留原字节回绕。最后实际弹栈恢复四个相机字节，重新写 `$0092..0095` 缓存。`$009C/$009D` 都被置为 `$90`，原旧缓存值不恢复。默认仅这两项行请求、显式 PPUSTATUS=0 时，共有62次真实 `$EEE6` 消费调用。

API为 `BattleBackgroundInitialization(shared_memory, pinned_rom_bytes, services=None)`，`run_entry(entry=0xA009, registers=..., return_pc=None)` 接受现有调用栈；`resume()` 保留同一 generator、相机栈和真正等待位置。`__call__(ServiceCall)` 可被统一 coordinator 路由：background要求映射 physical23/24，返回必须满足原 return_pc / expected_sp；外部 EE07 调用框架随后仍由其原 owner 恢复银行。没有服务时默认使用独立 `BattleNMIServices` 的 `$EEE6`。

硬件读必须由 `ServiceMemory` 显式提供；缺少 `$2002` 时保留待消费请求和已发生端口序列，不重放早先写入。`$EEE6` 仅处理高四位请求，低位仍由其真实 owner处理。验证中的低位文本例停在 `$A321/SP=F8`、`7E=11`：真实空文本消费者将cursor `$0304` 置FF并仅清bit0，得到 `7E=10`；背景恢复后再执行真实属性消费者，才到 `7E=0` 并返回。这个续程是源端 ownership 检查；原 CPU 对照只将该例计入严格前缀，不虚称额外完整 CPU 比较。

## F09C 原调用参数

`world_sprites_variant(registers=...)` 从 `$F09C BIT $0002` 开始。只有 `$F092` 外层会将 `$0003=0`、`$0004=F0`，本入口保留调用者传入的 tile offset 和纵向clip。它保留相机相减、flip、Y gap、负X补码不再加1的异常，X高字节拒绝前已经写下的部分OAM及cursor满FF的边界。直接方法的合同是正文结束 AXYP，caller拥有RTS；通过 `__call__` 则弹出已有真实caller并比较返回PC/SP。不默认完成DMA或画面帧。

## 原CPU对照和边界

**227个原 CPU 对照：224完整返回 + 3严格依赖前缀；另3个续程检查，0失败。** 其中直接tile/attribute行各32例，完整31组背景16例，F09C真实caller144例；缺PPUSTATUS前缀2例、未消费低位任务前缀1例。所有指令都由原只读 ROM 字节执行。

完整背景/F09C比较1979个RAM地址、全部8192B SRAM、有序端口写和最终PRG银行，以及AXYP/SP/PC。RAM只排除 `$01B4..01F8` 的空闲栈残留；真实palette/请求buffer/active相机栈与caller地址都比较。两个行primitive比较1940个冻结声明RAM地址和正文结束AXYP，calleeRTS的空闲栈残留不属于此合同。源码没有原 CPU callback、假ready或输出PCM。

输入来自阶段3原核心snapshot，并明确准备合法RAM0400地图描述符、相机、单位/strength/ruler、调用栈和sprite descriptor。它是受控CPU输入，不宣称自然可达。只读地图表限定合法chunk0..119，单位slot0..19、字形strength0..10及ruler0..6；未终止的sprite表、非法数据和decimal fixture不属于支持域。此轮没有新增原核心像素、中断周期或DMA验证。动态触及831个原指令地址；证据范围还包含复用helper的其他路径，不能视为所有分支完整覆盖。

```sh
.venv-trace/bin/python scripts/verify_battle_background_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_battle_background_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

- [独立源码](../../../source/recovered/battle_background_initialization.py)
- [CPU回执与依赖哈希](validation.json)
- [原bytes、数据表和合同](evidence.json)
- [正确含iNES header的原范围反汇编](original-ranges.asm)
- [实际执行指令位置](executed-instructions.json)
