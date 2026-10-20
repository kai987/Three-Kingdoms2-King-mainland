# 阶段21：独立被动观测核心

原ROM、原核心及阶段20文件未修改。官方135dfa6源码先作未修改重建，再新增独立被动记录核心；三种核心每种各fresh进程双跑同一自然冷启动F8接受路线。原始RGB、PCM、2048B RAM、8192B SRAM、完整serialized API buffer逐帧与冻结20数据比较，包含首帧前initial序列化时序，不补零、不截断或归一化。

[总证据](evidence.json) · [回执](validation.json) · [构建来源](core-provenance/build.json) · [独立补丁](core-provenance/observer.patch) · [脚本](../../../scripts/capture_city_auxiliary_watchpoints.py)

新内部总线日志只属于独立observer核心，不追认旧原核心有内部trace。每事件保留实际opcode PC、实际PRG页、寄存器、地址和总线值；写尝试与WRAM权限、后存储值分列。数组溢出即失败。word低/高事件是原Peek16表达式的逻辑分量，不宣称其内部子读顺序。

观察612个城市辅助字节总线事件，其中312读含300次原STA IndY dummy读取及12次BD97门槛读取；300写尝试来自原初始化清零和整城市模板复制。dummy读取和bulk覆盖不能给单字节命名或证明独立玩法。未命中只说明本条实际路径未观察，不能证明unused。

在野招募C71A扫描3次，每次237记录；C732计0，未实际随机招募或成功。E89A另有12组真实入口/RTS前边界，观察X保持；中断窗口语义须结合完整RAM53事件，不扩为普遍原子性。原10490/10491/10492关键检查点由完整cold路线保留，不使用较弱的13帧存档重入路径冒充同帧。

全48kHz实际PCM保留：observer案保存新全WAV，原控制和未修改重建的完整WAV先逐字节核同阶段20，再仅保留冻结原WAV路径与SHA，避免冗余文件。路径metadata JSON与0B VRAM不计入非空复跑。构建工具链不进入最终ZIP，官方来源、原文件、补丁与精确构建命令可复核。
