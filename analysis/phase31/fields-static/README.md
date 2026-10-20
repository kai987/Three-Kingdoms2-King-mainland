# 完整BC46至BDB8：一个条件名单写入合同

选中仅physical8:BDB8 `STA($00),Y`。冻结30分母1526=1200条件不交/81可能/245未知，经独立原CPU合同后变为1201/80/245、候选326→325。城市+1/+28..31正式名仍为null；条件地址排除不是reserved、padding或unused命名。

完整BC46正常mode0/1/2、当前及来源城市0..29、ruler0..6、binary且无NMI/IRQ/外部mutation的生命周期下，四个真实JSR为BC65→BD96→BC68、BD8E→BD96→BD91、BC8E→BD96→BC91、BCC9→BD96→BCCC。其输入03分别17、17..26、18..26、17。BE90以原F25F30切physical16，30行原邻接表均在8字节内遇负值，之前只含0..29；输出占用计数限定0..10，首轮跳0/10，第二轮仅0。没有由旧源码变量名推域。

F2AF全部原指令只写00/01，完整生成6000+32×rawcity；不改live03/04。BD96返回前不再调用未知callee，Y从03起，每次写后才INY/CPY27。父链Y17..26因此只写十个名册槽。权威ptr保守放宽到全部256个F2AF word，仍与150个城市辅助地址不交；不据此把rawcity30..255叫正常城市。optional PHA/PLA用0100..01FF，052C在RAM且不碰00..04，正常城市/全部F2AF目标都不别名ZP或stack。rawcity125可别名6FA1工作区并改变值或终止，这不是本合同未考虑的独立内存；地址界仍由完整ptr/Y决定。

裸BD96原03=1/27..31/255的反例保持：第一个非FF项总先写再CPY27，255会绕回0并继续写到26。更裸的BDB8中段可直接写scratch03/04、0800镜像、callerstack或6001/601C，均有真实单opcode前缀。它们不套完整父入口合同。mode2来源满城保留04=BD的原行为没有清零或Xclamp。三个受控BE55非平凡换位只证明原CPU行为，不冒充Native现场。

本矩阵13998案，13992实际callerRTS、6明确裸后缀前缀，另29模型/原字节/前提检查。包括7680typedBD96构造callee、6300完整BC46准备caller、7裸BD96异常offset、6裸BDB8前缀、3个经过早先FF洞才命中commander的换位callee、1个escape同值写及1个rawcity125真实后续别名案。每次selectedstore从prestate到真实opcode后write均导出；optional路径保留PHA→052C实际写→PLA→BDB8的SP/先后，两个同值STA也没有按diff过滤。rawcity125/03=18/04=16首store把下一工作项FF改70，下一轮实际读70，导致9次store而不是静态列表1次；它只属于raw store-addresslemma，不扩大正常父链域。Source病例0、Native帧0，不执行生产Source或控制IR、不用helperRTS替身。Bus保留全2048RAM/8192SRAM，所有原local/fixedhelper逐指令执行；没有声称另一Source全RAM/AXYP/ports差分。py65逻辑地址观察不等完整dummy微周期，原STA dummy在硬件仍可能出现。

其余1525项分类和权威address_contract不改；raw345逐项继承104操作数/13数据/228未证控制，未增加动态覆盖或声称固定点。完整父链终止不作普遍定理，输入列表或裸别名仍可产生更长/循环行为。矩阵自身有预算，实际各例正常返回或明确前缀结束；无中断是合同前提，不是动态IRQ测试。

复现：`python3 scripts/analyze_postbattle_roster_contracts_phase31.py ROM`；`.venv-trace/bin/python scripts/verify_postbattle_roster_contracts_phase31.py ROM`。仅写新31目录，旧30及更早文件不改。
