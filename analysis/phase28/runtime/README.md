# 阶段28：ECEE即时返回、子状态3异步等待与真实远调用

两个案例继续冻结的阶段27相同原保存点、相同普通无键输入：自然路线64帧、受控祖先路线32帧。本轮都是导入保存点，不是新冷启动，不新增任何核心内存/ROM/PC/RNG/request/ready/result/状态/名册准备。自然路线祖先准备0；受控祖先明确保留阶段15的19个战前数值字节及阶段3更早legacy准备未完全建立的边界。具体原before/after缓冲、每字节准备、来源链hash见每个stream的preparation.json。没有以同名冷回放替代真实母档身份。

固定原核心与独立28观察核心，各路线各两个fresh Python进程。共96首跑帧、384控制帧、8次状态导入、1074项非空artifact双跑检查、192 PNG和4 WAV。完整initial API调用顺序一致。每帧完整2K RAM、8K SRAM、实际256×240 RGB、48kHz stereo PCM和完整serialized state逐字一致，不截断/补零/归一化；还逐帧与冻结27原核心的96帧五缓冲hash一致。旧producer/core没有重跑或修改。0B VRAM不列入有效产物。

新核心SHA256：818969eae3c71133a9cebb5ef213a735ff4906768d7b3b055d1a1e71a76644b6。官方commit与真实来源、完整patch、原/改文件、清洁构建与强制watch-include重编日志在core-provenance；重编二进制字节一致。它是独立文件，不覆盖原核心或21/24/25/26/27观察核心。全局debug缓冲/选择token不在序列化对象中，不改游戏对象布局；只读const RAM/WRAM backing和实际PRG，不调用额外map.Peek/Poke、不增加模拟总线读写。事件或软件snapshot溢出硬失败。

68u32 ABI精确保留冻结27前48word，增加87..8A、7D..80、完整0100..013F palette backing与DE..E5银行影子。actual_PRG_banks由映射对象独立取得，不能用DE/E1/E2影子代替。写前值来自原store前const backing；写后RAM值来自新瞬时域，WRAM后值仍是原word17。控制器82..86写的post值没有独立快照，保留明确空值。CPU opcode_PC在Fetch前，旧last_CPU_opcode_field还是上一个opcode。word_read_low/high原名保留。原始事件和全84份10K软件上下文分别在bus-events.bin、events.jsonl、snapshots.bin、snapshot-index.jsonl。只有独立观察核心提供这些内部时点，未修改原核心只有独立五缓冲对照；没有瞬时N163/PPU/APU设备捕获。

真实原链为13:D4F0（先CC29）→D4F5 JSR EE07 /原Y28、inline A006→8:A006 JMP BAB3→sub2 BB93 JSR ECEE。D4F5完整实际软件现场已保留；它是CC29之后的中段入口，不证明Source覆盖CC29。EE07构造的原far返回栈、A006/BAB3/BB93/C027实参、四PRG、影子和返回边界均保留。自然与受控两条各有阶段2四个Source候选callee现场，另各有阶段3A006首hold及87负完成现场供严格未实现prefix验证。内部opcode标签不能一律当作独立JSR函数。EADE最终JMP没有额外hook，不应由返回栈虚构其immediate_transfer_PC。

ECEE是即时的palette请求初始化：ECF0写87=1，ECF5写88=0，ECFA写89=4，将0100..011F复制到0120..013F，然后ED18 RTS。同一帧恢复BB96，原SP增加2、返回word为BB95；它没有在内部等待fade完成，也没有初始化8A。本次两个母档旧8A都是4。紧接着BF0A、C027完成，BB9C推进0501到3，BB9F原RTS返回；此时87仍为1。INC的原总线先同值写2→2，再写2→3，两次write_attempt只表示一次状态推进。

sub3每次NMI重新经原far调用进入BBA0；不是保持21帧的同一个悬挂JSR或generator。local2..20共19次，BBA3读取87=1、N=0而走BPL→BBB7原RTS；每次自己的SP/真实caller栈保持对应，跨帧SP可以因原主线程中断位置而不同。EC67消费真实旧8A，在local6/11/16/21将88推进1/2/3/4；四次各32个原palette store。local21原EC95写87=FF，同一帧BBA0观察负标志后到BBB8清理并切global1。这个21帧仅是这两个实际母档旧计时器4的观察，不是ECEE通用固定时长，也不是人工ack。

原EE07返回恢复codepair及E2；F25F数据页E1副作用不回滚。实例首次D4F5四PRG为17/12/13/31、影子E1=49，EE52为16/12/13/31、E1=48，E2恢复44。完整数据见palette-lifecycle-observations.json，不能简写成四银行全部恢复原值。

local24另一次ECBF开始城市场景的新fade，已作为later_independent_palette_requests分列，不能算成本次ECEE完成或再次恢复原caller。自然终点是worldmap/city0-sub1；受控祖先终点为真实淡出画面/city13-sub0，不能描述成已完成可见的城市资料页。

本轮Native还真实重见继承G106的15逻辑LDA、11个STA dummy、11次store（7字节改变、4同值），以及后续C027供给返还；这些在postbattle-observations.json单列，不能拿帧末金粮9999否定此前扣减。它不是本轮新发现的资源公式。城市150辅助字节事件为0，仅是此路径有界观察，不证明unused、正式名或全ROM完成。

Source仅覆盖阶段2及明确中段bridge；Native观察到后续sub3等待/清理不把Source3升级为闭合。Source差分、共同显式设备夹具、独立CPU合同、Source未实现prefix、观察核心事件和未改核心五缓冲是不同证据域。后续CPU比较如需N163，必须明示其共同夹具而非瞬时Native设备状态。
