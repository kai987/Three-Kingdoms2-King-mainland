# 内政次级策略：具名源码、等待与真实消费者

[DomesticSecondaryServices](../../../source/recovered/domestic_secondary_services.py) 用具名直接 Python 替换上一轮复制控制形态的 B5FC 次级分支。新body锁定 physical10 的523个原指令位置；B49C两轮分配、BD7A补兵与共享指针/整数/RNG/邻接/名册 helper复用冻结源码。生产不运行原 CPU、IR或动态程序表。原 phase1..18 代码、回执和原核心证据保持冻结。

## 三个分支及作用顺序

B5FC调用E89A，取返回值低7位，拒绝>=90；0..29走BBB2降忠，30..59走B98B招揽，60..89走B619邻国资源交涉。主B49C的E8AA仍先拒绝>=50，只有0..9进入此B5FC；原始采样和cursor推进全部保留。

B619先选本势力非leader最高忠诚使者（平分后者），要求至少3个leader不为FF、本ruler四个外交byte的8bit和为0、至少两个其他owner邻居。它在邻居中选城最多者（平分后者），并要求目标城数严格大于本方城数+2。q=floor((目标城数×30+70)/10)，原随机选择金或粮，完整报价为4q/6q。原 affordability 用042F/0430完整word，但提交缓存3A取042F、3B却取始终为0的0431，因此实际资源转移截为低byte；24城边界原CPU已对照报价316/474、提交60/218，资金255会在fullword检查处失败。目标controller整个byte恰好3直接写双向外交nibble A并转资源，其余byte先发F8再等待回复，不能把low2==3当整个byte==3。

B98B选择本方prefix人数最少且小于10的城市（平分首个），再全外方名册选忠诚最低且<70的武将（平分首个）。成功后依次追加到目标首FF、重新计算忠诚、在原城删除并压缩名册；原城无prefix武将时将owner整个byte写7。随后才对非controller3方发FA通知。它不写武将HP、status、驻城byte5或兵数。概率中有原始 quirks：读取IQ并做IQ+徳的ADC后，该A被覆盖，除法实际只用先前21中存的徳；等级差按8bit符号处理，不改写为通常的有符号公式。

BBB2先找本势力最高IQ，然后选非本方且controller整个byte不等于3的最大prefix名册城市，必须至少6人（平分后城）。在其十个槽中收集忠诚50..89的候选，再原随机挑选。成功概率含max(0,本方最高IQ−目标IQ)+难度表byte，所有加法保留8bit。先把目标忠诚扣去 floor(本方最高IQ/20)+原随机1..7，再发F9通知。兵数高位、HP、status和驻城字段不因此重写。

## 等待保持同一 caller

F8在B78B等request!=F8，且只有回复0接受；F9/FA分别在BD36/BB40等request==0。`SecondaryRequestWait`保留原SP和同一个generator；resume重复观察，不写请求/ready/result或假RTS。缺fixed服务同样停在真实callee帧，非returned状态即使伪装PC/SP也不能通过。

真实城市消费者是NMI2的26C7E0：F8进入city9/phase16三级询问，F9/FA分别进入phase15/14通知。原文字消费者完成队列，原按键/菜单最终令CD6F把040C写回request；不是测试程序替它确认。四个长序列分别为接受0/拒绝1各85显式NMI+425IRQ，FA/F9通知各61NMI+305IRQ；每序列只计一个父case，最终恢复原暂停controller并RTS至真实caller E188。起始资格和地缘/controller是明确CPUfixture；这些事件不是视频帧时序，更不是Native F8实机记录。后续输入只有普通controller ports与显式中断，没有ready/ack注入。

## 验证及覆盖

正式矩阵 333 次原CPU对照：278 实际caller RTS、53 原循环等待、2 缺服务前缀；另 9 个源码guard。另四个消费者父序列单列，不重复加嵌套中断/callee准备数量。每个边界比较全部2048B RAM（含free-stack）、8192B SRAM、AXYP/SP/PC、有序IO、四PRG银行、N163全部128B/地址/自增。新phase19总线按官方原核心实现127→0回绕；旧冻结ServiceMemory的饱和行为不用于本轮比较。source CPUcallbacks=0。

真实 Native 保存格式现在可解出REG七字节、实际MAP/PRG/BNK与N63/SND/RAM；原CPU发现从这些真实捕获上下文开始，使用实际银行而非DE..E0影子。83个冻结母点的有界、无新增NMI/IRQ原CPU前序捕获了B5FC/B98B/BBB2三个真实callee入口（B5FC和B98B来自同一母点不同边界）；这些入口对应3次source比较，原prefix steps不额外计case。未捕获B619的自然入口，未把任意PC/修改RNG当自然发现。独立原CPU续行仍不是原核心内部逐指令trace，也不还原之后的硬件时钟。

以 phase18 static739 的物理bank/PC集合为固定目标：原动态267，旧缺口472；新矩阵补到其中464，四consumer再补7，合计471。联合旧证据共738/739；剩BCDC LDA0没有动态覆盖。其正常入口界限是目标忠诚>=50、最大byte IQ255/20+7=19，故SBC不会借位，BCDA必走BCDE。保留该原始防御分支和字节证明，不用绕过资格的局部fixture冒充正常可达。指令位置覆盖不等于全部路径/输入空间/时序已验证。

城市+1与tail28..31在这里没有获得新的正式名称；原真正重叠门槛和其他访问仍按前轮明确合同记录。本轮正式原核心零写入扩城/月轮窗口未观察F8，不能用CPU受控成功淡化这个缺口。

## API与复现

```python
rules = DomesticSecondaryServices(memory, rom, services=readable_services)
rules.run_entry(0xB5FC, registers=actual_caller_registers)
rules(service_call)  # exactphysical10/11与PUBLIC入口
rules.resume()      # 原等待未得到真实reply则继续waiting
```

PUBLIC=A000/A00F/B49C/BD7A/B5FC/B619/B98B/BBB2；LOCAL只公开给明确局部CPU测试B78B/BB40/BD36。Root新增DomesticSecondaryGameEngine/SceneCoordinator路由和真实context factory，不改旧GameEngine。B5FC三个算法均直接具名函数，不在运行时读取program.json、opcode或PC字典。

```sh
.venv-trace/bin/python scripts/trace_domestic_secondary_callers.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_domestic_secondary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_domestic_secondary_interleave.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_domestic_secondary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[原汇编](original.asm) · [原字节目录](static-catalog.json) · [完整矩阵](validation.json) · [覆盖交集](coverage.json) · [未覆盖界限](unexecuted-clamp-proof.json) · [四消费者交错](../cpu/consumer-sequences.json) · [实际caller](../cpu/actual-callers/discovery.json) · [原核心](../runtime/README.md) · [证据hash](evidence.json)
