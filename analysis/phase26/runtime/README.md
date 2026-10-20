# 阶段26：自然部署坐标指针 G107

本轮从冻结的 `phase11/runtime/cold-battle/battle-enter-confirm.state` 继续。原案例回执记录为无导入、无数值/结果/ready准备的真实冷启动普通输入路线；该保存点是其第5626帧。新案例自身导入保存点，不能称新冷启动。祖先与本轮全部准备均为0，精确来源见每个stream的 `preparation.json` 和根 `evidence.json`。

普通输入只有 A35帧、松开125帧。固定原核心与独立26观察核心各用两个fresh Python进程重放。完整initial序列化调用顺序相同；每帧原始2K RAM、8K SRAM、256×240 RGB、实际48kHz stereo PCM和全部serialized state均一致，不截断、不补零、不归一化。每一帧PNG/2K/8K/state、完整WAV、callbacks与正式JSON还做同核心两跑精确对照。

观察核心独立文件、独立hash与来源补丁在 `core-provenance/`；未改原ROM、固定核心或21/24/25观察核心。首次编译使用干净新树，Makefile显式依赖watch include；强制更新include触发CPU重编，重建二进制逐字一致。新hooks只读CPU/PRG/物理RAM和WRAM backing，不调用map.Peek、不增加仿真总线读写、不改变可序列化对象布局。44u32 ABI与原始日志详见 `observer/event-schema.json`，溢出会失败。

实际local139命中 B130、B1B0、B2AE，side0、非统帅数量3。B312在本路线未经过，不能称自然覆盖。四个G107逻辑位点共8次读取，实际20/21=8D4E、数据物理bank6；逐读及后继单位坐标写见 `deployment-observations.json`。完整原始ROM总线日志也含指令/操作数字节取指，不能把所有read事件当作字段消费者。帧末指针和银行不能替代这些opcode时点。

三个实际entry保留全部2K/8K、AXYP/SP/PC、真实四PRG、原软件返回栈。B130可由原JMP进入，不假造JSR caller。瞬时N163/PPU/APU设备状态没有捕获；后续Source/CPU验证如需该设备环境，必须另列显式共同夹具。

最终global4/NMI3、battle10/sub4。原初始化和后续场景执行都由核心完成，没有伪ack、跳PC、RNG或结果写入。未观察到150个城市辅助字节的总线事件仅是本160帧路线的有界负结果，不能证明unused或官方字段名。不是战役胜利、Source循环模拟器或整个ROM完成声明。
