# 阶段29：原机战后城市归属与名册收尾

本层续行阶段28完全相同的两份母档及普通无键输入，新增独立被动核心对 BBB8/BC00 的瞬时观测。它没有重新玩一场自然胜利，也没有向核心新增数值、状态、结果、ready、ack、RNG、PC 或名册准备。

## 正式范围与来源

| 路线 | 导入母档 | 本次原始帧 | 祖先准备 |
| --- | --- | ---: | --- |
| natural-postbattle-skip | 阶段22 observed-g04-n03-battle-015-002，原 frame7636 | 64 | 自然普通输入祖先，已声明数值准备0；本层仍是存档导入，非新冷启动 |
| controlled-ancestry-resource-loss | 阶段15 succession-heir observed-g04-n03-battle-015-002，原 frame8051 | 32 | 继承阶段15已记录的19字节数值准备；更早 phase3 legacy 准备未完全建立，不假设0 |

精确母档、SHA、逐字节准备、before/after 2K/8K 缓冲和更早导入链都在 [evidence.json](evidence.json) 的 `case_ancestry` 及每流 `preparation.json`。与固定原核心对照的本次8次运行均 `state_imported=true`、`cold_boot=false`、`additional_core_memory_writes=0`。

固定原核心 SHA 为 `924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a`。独立29观察核心 SHA 为 `532d6a9113eaef571f56cc1717f97e0d2b39cbb94cb48b01b9886116c54c70cb`，与原核心、21/24/25/26/27/28观察核心均为不同文件，旧文件未改。ROM SHA 为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

## 完整输出对照

[validation.json](validation.json) 已通过2路线、8个 fresh process，首份原核心合计96帧、全部控制运行384帧。每帧 RAM2048、SRAM8192、原RGB、原PCM、**完整原始 serialized state** 五类缓冲，均在固定原核心与独立观察核心之间精确相同；各核心的第二个 fresh process 也逐产物精确重复。没有补零、裁剪或归一化 serialized buffer。

首次 serialize 在新核心启动后、导入母档前执行，然后保存导入后 initial.state/2K/8K；这份调用日程及初始缓冲也精确相同。新增原核心96帧的五缓冲还逐帧等于冻结28对应记录，仅作只读继承一致性检查，未重跑旧生产器。

- 1182个非空产物重复检查；192对PNG与4对WAV。重复目录位于 `../runtime-repeat/`，数字不把两份相同文件另算新病例。
- 256197个原始被动事件，120份完整软件上下文（自然56、受控64）。全量原始日志及 ABI 在各 observer 目录。
- PNG保持原始256×240；WAV为原核心实际48kHz、stereo16bit输出。逐帧 PCM hash 与完整WAV对应，没有生成替代图片或声音。
- [media-static-validation.json](media-static-validation.json) 是静态图像/音频及重复产物核对，不新增CPU或原机帧数；交互播放验收另由根门户完成。

## 新观测到的收尾

[completion-lifecycle-observations.json](completion-lifecycle-observations.json) 按原事件序号关联 BBB8 入口、BC00 每次真调用、真实读写、指针临时复用及父返回。

两条路线均在本地 frame21，原 `$87` 已由 NMI 淡出驱动写成 `$FF` 后，进入 BBB8。原 BBA0/BBB7 的先前19次保持都是每次NMI新调用；ECEE在 frame1 已即时RTS，不存在悬挂21帧的同一个JSR。本轮继续保留 [palette-lifecycle-observations.json](palette-lifecycle-observations.json) 作为这一反例回归。21帧取决于当前母档的旧 `$8A=4`，不是通用固定时长；frame24的新淡出是另一个场景的请求。

BBB8 从真实城市ID4取城市指针；outcome0的受控祖先路线在 BBDD 将地址 `$6080` 从1写为2。自然 outcome1 路线跳过这个 owner 写。之后两案均读取真实 bank16 邻接表，依次得到 `2,12,11,3,1,FF`，故 BC00 实际访问6城：`4,2,12,11,3,1`。此前只看发生名册写入的城市不能推断调用总数。

BC00将 live `$00/$01` 城市指针复制到 `$0A/$0B`；F368随后把 `$00/$01` 改为君主记录指针。原 owner 使用低4位，只有编码7直接早退。名册扫描包含偏移17..26全10槽，不以 `$FF` 提前结束。实际未找到君主的城市会完整扫描后返回，本次不是所有访问都有换位。

| 原始访问类别 | 自然路线 | 受控祖先路线 | 合计 |
| --- | ---: | ---: | ---: |
| 逻辑城市读取 | 34 | 43 | 77 |
| 邻接ROM读取 | 6 | 6 | 12 |
| 君主记录读取 | 6 | 6 | 12 |
| 城市真实STA写尝试 | 8 | 7 | 15 |
| STA间接寻址dummy读 | 8 | 7 | 15 |
| 实际改变的字节写 | 0 | 1 | 1 |
| 保留原值的名册写 | 8 | 6 | 14 |

14次名册写均保留原值，本次不称“原机已观察非平凡名册换位”。完整city32B记录、owner、名册与150个辅助字节在每帧字段中保留。本次辅助域总线事件0只是这两条有限路径的观测，不能证明这些字段未使用，也不给 `+1/+28..31` 新增正式名称。

## 真实软件上下文与设备边界

每流保存 `snapshot-index.jsonl`、原始 `snapshots.bin` 以及 `callee-*.json/-ram.bin/-sram.bin`。它们来自独立29观察核心的真实 pre-opcode 边界，保留 A/X/Y/P/SP/PC、原栈和4个实际PRG银行；不是固定原核心原本提供的内部trace，也不是全指令trace。

稀疏上下文包括实际 A006/BAB3/BBA0 的首个hold与完成调用、BBB8、全部6次BC00及其返回，以及D4F0/CC29在frame1与21的真实入口。CC6D与CC92/CCAC原字形读取、CCDF指针增量也有只读事件，不把后续frame末复用的指针倒推成较早逻辑读取。

没有瞬时N163、PPU或APU设备快照。独立CPU/源码对照若用共同N163环境，必须单列为显式fixture，不可称原机瞬时设备上下文。原EE07恢复代码银行但不恢复callee改变的数据页；4银行和DE..E5影子均保留，影子不冒称实际mapper状态。

## 观察核心可复核来源

[core-provenance/build.json](core-provenance/build.json) 记录官方commit `135dfa6dfda5e7603d61e751b9ddd0cc42546bc3`、冻结28补丁、新29全量补丁、编译器、clean/build/include依赖重编译日志及所有源文件SHA。新树从原官方本地仓库克隆后独立构建；显式include依赖重编译所得二进制逐字节相同。

68-u32/272B ABI布局沿冻结28，独立API名为 `nestopia_completion_*`。新增仅CPU原操作边界与const RAM/WRAM backing复制；没有额外模拟总线或设备读写，没有修改模拟器对象布局。事件和快照溢出会明确失败，不静默丢弃。word_read_low/high按真实读kind解码，逻辑读取与STA dummy、write attempt与实际changed byte分别统计。

新生产器为 [capture_native_postbattle_completion.py](../../../scripts/capture_native_postbattle_completion.py)。只应向新目录运行；拒绝覆盖正式输出。阶段28和更早源文件、核心、存档与版本归档均保持冻结。
