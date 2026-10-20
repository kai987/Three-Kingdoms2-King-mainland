# 阶段27：G106 战后城市指针的实际控制分支与写入

本轮只继续两个冻结保存点，普通输入均为无键等待。没有新增 ROM、RAM、SRAM、PC、RNG、request、ready、result 或名册写入。两个案例都导入保存点，不是本轮新冷启动。

- `natural-postbattle-skip`：阶段22第7636帧，祖先是阶段14真实冷启动普通输入路线，已声明祖先数值准备0。继续64帧，实际 BF0A 入口 outcome `$0514=1`，在 BF0F 返回，没有执行该服务的城市读取、随机抽样或资源写入。终点 global2/NMI2、city0/sub1。
- `controlled-ancestry-resource-loss`：阶段15第8051帧，继续32帧，实际 BF0A 入口 `$0514=0` 并完成资源处理，再返回父流程。阶段15在原战斗前明确准备过19个数值字节；其前序为阶段3 `attack-intro-7.state`。更早17段 import/button 元数据没有充分记录所有可能的数值准备，故不宣称更早准备0，不用后来 cold-replay 的同名文件替换实际身份。全部已知准备、原before/after 2K/8K和历史链hash在各 stream 的 `preparation.json`。终点 global2/NMI2、city13/sub0，原屏幕处于淡出状态，不能称已完成可见的城市资料页。

固定原核心与独立27观察核心，各案例各自两个fresh Python进程。合计96个原核心首跑帧、384个控制帧、8次状态导入、864项非空artifact双跑检查、192个PNG与4个WAV。全部 initial API 缓冲以及每帧完整2K RAM、8K SRAM、256×240 RGB、实际48kHz stereo PCM、完整序列化缓冲逐字一致；不截断、不补零、不归一化。完整WAV/回调与每帧PCM hash独立核对。0B VRAM没有列入有效产物。

观察核心身份为 `4e8df712fb9193474abcc089bc34b9d6c764f1f5ac96075bc9ef8b5da66fc6c2`，独立于未修改原核心以及21/24/25/26观察核心。`core-provenance/` 保留官方commit、原/补丁源、统一patch、清洁构建和强制include重新编译日志。重新编译二进制字节一致。新增hooks只读CPU/实际PRG/物理RAM和WRAM backing，不调用额外map.Peek/Poke，不改变可序列化对象布局，不增加模拟总线读写。前值是原写入前的const backing读取；后值是原写入后的WRAM backing读取。写事件仍叫写尝试，不能仅凭调用假定可写。

原始48u32 ABI、全局连续序号、actual opcode PC、bus PC、实际四PRG、完整ZP00..2F、堆栈及前后backing定义见各 observer 的 `event-schema.json`；事件或snapshot溢出均硬失败。旧CPU opcode字段在pre-Fetch边界仍是上一opcode，不能当当前指令。内存镜像、字读取的 `word_read_low/high` 原始名称均保留。稀疏软件上下文来源是独立观察核心，固定原核心没有内部trace；瞬时N163/PPU/APU设备状态没有捕获。后续CPU/Source如需这些设备，必须单列显式共同夹具。

两个observer共17,378个事件和14份完整2K/8K软件入口。新G106四入口实际上下文共10份：自然BF0A一次；positive BF0A一次、BF9E五次、BFB3一次、BFEC两次。另有两个BAB3 parent和两个C027上下文。所有入口保留实际AXYP/SP/PC、四PRG和原caller栈；BF0A真实返回字为BB98（RTS到BB99）。最后BF9E由BF9B尾跳进入，SP与父返回字保持原值，没有伪造JSR。

Positive实际 `$1A/$1B=6080`、城市4、四PRG `[16,8,9,31]`。五个LDA位点共15次逻辑读取；BFDF/BFE9共11次STA写（低6/高5），另11次STA IndY原始dummy总线读取单列，不能混入LDA。11次写中7字节改变、4次0再写0。原word offset6、8、14从9999变2445，byte11从100变90；offset2和4均0再写0。此处保持原偏移标签，不由数值扩张正式字段语义。每次读、store、实际EA/Y/A、前后backing、银行与栈在 `postbattle-observations.json`。

紧接着父BB99调用C027，金/粮位置出现0→9999，是补给返还后的另一段原写入，不是BFDF/BFE9的扣减结果。`following_other_city_gold_grain_writes`单列其实际PC和EA。帧末最终资源不能替代扣减时点，帧末复用的1A/B也不能倒推过去指针。

本96帧路线未出现150个城市辅助字节的总线事件，只是有界路径观察，不证明字段unused、没有写者、已命名或整ROM完成。零新增写与受控祖先准备分列；Source CPU病例、独立原CPU合同、观察核心事件和原核心缓冲比较均是不同证据范围。
