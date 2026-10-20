# Phase 1：64字节数据包生产与真实返回

本轮闭合 `A06F →29:A039 →BC74 phase1 →BC9B..BD02` 的实际64B生产与返回链。10个受控父案例、25次生产调用均通过独立可读Source/原ROM CPU对照，共11,562条原CPU指令。全部真实执行BD02 RTS，再经EE4D恢复代码页、EE52 RTS到A074首条指令之前。没有新增游戏算法或重复实现已有正文。

## 实际流程

| 步骤 | 原逻辑与验证结果 |
|---|---|
| BC9D/F25F | Y=30，raw E1=30、物理8000数据页16 |
| BCA2/BCA8/BCAE | 0380..0382 写入40、原目的高字节、原目的低字节 |
| BCBF/BCC1 | 按Y=0..63逐字节交错读源、写0383..03C2 |
| BCCB | Y=40时在03C3写FF终止符；64B生产不因payload字节值提前结束 |
| BCD1..BCEC | 源和目的分别独立CLC、加0040，保留页进位 |
| BCF0/BCF4/BCF7 | 更新后目的高字节等于28便推进0401并真实调用ECEE；不要求完整地址等于2800 |
| BCFF | 无条件007E |=04，表示请求；没有producer busy/ready guard |
| BD02/EE4D/EE52 | 真返回并恢复代码页27/28，保留E1=30和数据页16副作用 |

祖先来自上一包 `all_SP_values/0000` 已冻结的两侧相同phase0后态：PC=A074、A=3B、X=00、Y=3B、P=30、SP=00；PRG=[17,27,28,31]；007D=3A、007E=1、0401=1、0470..73=00 88 00 24。每次只显式把PC重入A06F、Y改3D；独立边界例另有预锁RAM补丁。跨包输入是文件fixture，未声称跨包同一活进程或自然场景连续。

首包实际结果：header=`40 24 00`、64B来自8800..883F、03C3=FF，源推进8840、目的推进2440、phase仍1、007E=05。25次各执行64读/64写，共双方各1600次payload读取与1600次payload写入；1552读来自物理16，48读来自物理29。9FF0跨窗例的A000..A02F仅作为数据被读取，没有opcode执行信用。

同一父案例内，Source和CPU各保留自己的engine/bus，受控重入16次：前15次phase1，末次目的27C0→2800后phase2，源最终8C00。这16次会覆盖同一个待上传包，不能称1024B已经上传、真实ready或自然NMI调度。其他边界覆盖007E=0/4、源单独进位、目的单独进位、27D0→2810仍推进、28BF→28FF仍推进及28C0→2900不推进。

4次ECEE均调用既有精确Source owner并由ED18真返回：87=1、88=0、89=4，将调用当时0100..011F复制至0120..013F；不写7D/8A、不等待淡出结束。SP00继承的活动帧为0100与01FF..01FA，与备份区不交。SP20..45的栈别名危险范围未纳入正例，不宣称任意SP都能返回。初始外层栈字节仍是受控fixture；本轮只证当前真实JSR/farframe，不构造或消费outer RTS。

## 源码与复核

本轮直接使用既有 `source/recovered/global_ui_controller.py` 的 `CityUIWorkers.cityuiworkers_bc74_phase_1`，通过真实 `SceneCoordinator →GlobalUIController.city_workers` 路由；`F25F`、`ECEE`由既有共享Source服务执行。冻结上一包的 `readable_entry.current_jsr` 只接入当前调用，Source先独立运行，未接收CPU输出或CPU/IR回调。生产源码无需重写，新增测试仅验证此有界数据流。

每次保存初态及forward、F25F后、callee真返回后、EE52真返回后的完整2K RAM+8K SRAM，后四阶段双方分别保存。逐案记录完整REG/PRG/raw ports、原CPU指令和栈写、两侧真实payload读写顺序与Source方法/行号。ECEE还分别保存两侧实际进入/返回的完整RAM/SRAM。离线复核从初态重放日志写入、逐字节比较双方buffer，不重跑游戏代码。

- [预锁范围与原字节](family-scope.json)、[矩阵](case-matrix.json)、[预锁验收及实现哈希](acceptance.json)
- [实际执行](run-01/validation.json)、[逐案证据](run-01/cases.jsonl)、[离线验证](semantic-validation.json)
- [生产与阶段证据](producer-state-evidence.json)、[BCBF访问关系](bounded-access-evidence.json)、[全局工作包增量](work-package-delta.json)

## 尚未覆盖的消费边界

007D=3A始终保留，来自旧fixture公式而非Native/PPU ack。phase1本身没有busy判断；后续EE53会优先走palette。实际消费需要单独预锁调度、2002读值/时序及2000/2006/2007写入合同。已有精确TextSceneServices A006/A11B算法，本包没有因此发现未知WP07算法；缺的是仍待验证的设备与调度合同。见[最小设备合同](device-contract-boundary.json)。本轮消费、NMI/IRQ、新Native和outer RTS执行均0，未宣称完整WP08或长期战役闭环。

## raw228的实际payload消费者

动态记录确认本轮实际读取4个raw窗口：`/windows/136`（b16 off08E4）、137（off09E7）、138（off0A62）、139（off0A63）。在16次序列中分别位于零起算step3/Y36..38、step7/Y39..41、step9/Y34..36与Y35..37；对应可读case key是step-04、step-08、step-10。每个字节都同时保留实际CPU BCBF读取与Source方法/行号记录。

138/139重叠2字节，共12条window-byte关系、10个唯一ROM字节；不能重复算作12个独立字节。它们得到payload数据角色证据，不证明raw起点opcode已执行、也不排除其他入口；raw分类及共同语义根保持原样。见[逐字节消费者证据](raw-payload-consumer-evidence.json)。

## 固定账本与封存

BCBF保持原canonical ID `b29:cpuBCBF:rom03BCCF`，全账本索引1474、当前remaining索引282。其18个受控源基址和1600次实际读取补充有界证据，不迁移整条访问分类。raw249前两字节仍由EE1F/EE25作为A039 inline地址消费；本包延伸同一A06F的phase1，不增加第三个caller。155个冻结直接EE07 callsite中，跨两包仍纳入2个、其余153未由这些包覆盖；153不是全局未知服务数。

1526=1203 conditional/80 possible/243 unknown、remaining323和raw345=104 operand/13 data/228 unproved全部对象与字节保持。城市+1、+28..31正式名继续null。旧239445路径、上一包39文件及5脚本共239489路径前后冻结；所有旧件保持不变。不发布、不推送、不分发ROM。本包完成后停止。
