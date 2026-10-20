# WP07：调色板优先处理 → 首个64B包消费

本包从phase1主序列step-01的实际后态出发，完成两次真实 `31:F8B5 JSR EE53`：先输出32字节调色板，再输出64字节packet，分别由E748/A152真RTS回固定31:F8B8首指令之前。5个受控父案例、10次实际调用通过独立可读Source/原ROM CPU对照，共2630条原CPU指令；两处缺输入各一次零进展重试及真实恢复也通过。

## 来源与真实调用

祖先只取前包CPU/Source双方相同的offset0、10240字节，SHA256 `28c408c54d3228dc2c3ab0e5a8a417f06deae0b6b34da01db6aa2a602bf27e0a`。它是首包后态：007D=3A、007E=05、源8840、目的2440、phase1；REG A074/A3B/X00/Y3B/P30/SP00，PRG[16,27,28,31]。没有取step16，也没有倒填后15个已覆盖包上传的信用。

每次仅将PC受控转至实际callsite F8B5；第二次从真实返回F8B8再次转至F8B5，其余寄存器、SP、RAM和银行由程序保留。callsite原字节2053EE，真实JSR压F8B7；Source复用已有BattleNMIServices.call，既有SceneCoordinator把A006尾调用交给TextSceneServices。没有hostpush、seed返回帧或Source CPU/IR回调，也未执行NMI入口、硬件中断frame或F8B8的下一条F206调用。

SP00使本次真实JSR先写0100=F8、01FF=B7，所以palette首字节实际是F8，祖先的A0已被真实建帧替换。上传期望取建帧后的live0100..011F。这是受控栈别名事实，不是自然palette画面验收。

| 调用 | 实际路径与结果 |
|---|---|
| 第一次 | 7D3A→EE56/EE72→E70E；E713写2000，E716读一次2002；E71B真实清7D；写32个2007 palette值；E748 RTS→F8B8。7E仍05，代码页仍27/28。 |
| 第二次 | 7D0/7E05→EEC3真实清bit2为01；EEC8/F237选29/30→EECB尾跳A006/A11B；A12D第二次读2002；地址2400写64B；FF结束；A152直接消费同一个F8B7 frame→F8B8。 |

第二次最终E1/E2/E3=30/3D/3E、PRG[16,29,30,31]；不是EE07，不恢复旧代码页27/28。007E仍bit0=1，不称全部job清空。phase1已生产的queue字节与城市SRAM均保持。

## 明示的软件设备合同

旧包只保存2K RAM+8K SRAM，没有PPU内部状态。本轮PPU初态另行声明：16K raw sink字节公式、地址、地址/滚动latch、增量和端口影像均为受控fixture，未获得Native或自然时序祖先信用。

完全复用现有ServiceMemory：有限2002样本队列，无repeat或自动填值；成功读会消费样本并重置其ppu_latch/ppu_scroll_latch；2000的bit2控制1/32增量；2006按高低两次写14位地址；2007按原14位地址保存完整原byte并递增。不同样本00、80、40、FF及非零latch初态均已覆盖。这两处LDA2002不轮询、不测试状态位决定ready，样本是外部软件输入而不是vblank完成许可。

该bus没有内部PPUSTATUS/vblank产生或读后清bit7模型、开放总线、CIRAM/CHR或palette物理镜像、palette6bit掩码、周期、NMI边缘或渲染。因此只证明有序软件端口命令和原始地址sink；不能从Source/CPU共用此模型后相等，推导真实PPU正确。F8是原始2007命令值，未当作已渲染颜色。见[预锁设备合同](device-contract.json)。

## 缺样本与恢复

| 边界 | 已发生并保留的前缀 |
|---|---|
| E716缺样本 | 2000已写；7D仍3A、7E05；尚未palette数据输出。 |
| A12D耗尽 | bit2已由真实EEC3清为01，代码页已切29/30，00/01=0380，2000已写；64B数据尚未输出。7E01不代表消费完成。 |

Source停在既有ServiceWait；CPU在缺样本读指令之前gate，不半执行后修复PC。重复无输入续程无内存、REG、设备或IO进展，不重做2000或建帧；同Source owner、pending call、generator链和位置动态断言保持。仅向两侧设备输入deque追加预锁剩余样本后，原对象继续执行并真实返回。成功2002总计10读；两个缺样本位置和两次重试不额外计为成功读。

## 复核与可读源码

5父案均526条原CPU指令。逐侧palette160读、packet340读（含每包3B header/64B payload/FF），500次数据读值与顺序一致；原始2007输出palette160B、packet320B。每父110个交织端口事件（2读+108写），Source/CPU逐事件kind/address/value及设备before/after全部一致，来源标签单独保留：Source使用实际方法/行号和语义PC，original_PC为null；CPU使用实际opcode PC。

44对完整保存点包含2K RAM+8K SRAM+16K raw sink及REG/银行/完整声明设备JSON；双方各1171456字节。保存了初态、受控call起点、真实JSR后callee入口、packet尾入口、每次暂停/零进展重试/恢复/返回。离线从初态和实际软件/端口写前缀逐点重建所有44份内存与raw sink，核对交织事件；离线审计没有重跑游戏。

实际正文仍来自已有 `battle_nmi_services.py` 的pending_ppu/palette_upload/mapper_window以及 `text_scene_services.py` 的packet_consumer_entry/consume_nametable_packets/write_nametable_packet_tiles；新[入口与观察适配器](consumer_adapter.py)只复用这些算法，新增游戏/硬件算法均0，旧生产Source未改。

- [预锁范围](family-scope.json)、[有限矩阵](case-matrix.json)、[验收和112项执行pins](acceptance.json)
- [实际执行回执](run-01/validation.json)、[逐案原指令与Source证据](run-01/parents.jsonl)、[44对保存点](run-01/points.jsonl)
- [离线复核](semantic-validation.json)、[严格恢复证据](strict-input-recovery-evidence.json)、[状态与命令证据](status-and-command-evidence.json)

## 全局范围与剩余前提

WP07新增闭合的是本首包在有限输入计划和原始地址sink上的生产后态→palette优先→packet消费→真实返回及缺样本恢复合同。WP08获得可复用的有界文件fixture片段；真实NMI/IRQ/main连续调度、原PPU现场/时序、残余bit0和后续F206/FB0B均未纳入，完整WP07/WP08仍未完成。见[工作包增量](work-package-delta.json)。新Native、自然入口、旧outerframe和显示信用均0。

首个palette返回的实际87..8A仍为 `5C 79 96 B3`。真实F8B8的下一条是F206（已有CHR配置，发8个CHR写），随后FB0B在FB22的BIT2002/BVS按bit6等待，需要本包未声明的新位置有限样本，不能预言它必定返回。只有FB0B实际返回后才到EC67；本包第二次直接重入F8B5，跳过了这些未执行的continuation。仅按冻结Source静态推导：若后续到达EC67且这些字段未变，8A从B3减为B2后为负，便重装96、重新置7D=1，88变7A并使87变FF，再执行palette更新。F206本身不会重新置7D，palette_fade属于EC67。因此自然下次EE53不保证选择bit2；该调度必须另包验证。EC67还会写活动palette区，SP00的frame别名与实际返回同样不能预设成功。本条是静态剩余前提，未执行或增加测试信用。见[continuation前提](continuation-preconditions.json)。

packet A132/A13A/A140/A146是全账本1405..1408原已disjoint的四个typed点，不重复减少323。palette是absolute,Y读，不增加typed间接访问。旧raw136..139的16包覆盖不继承为本次consumer证据，本次消费只读取首包RAM数据。

1526=1203/80/243、remaining323及raw345=104/13/228全对象/字节分类保持；城市+1/+28..31正式名仍null。155个EE07已知caller/跨包2个/外部153的口径不变，153不是全局未知服务数。239489旧路径加phase1的34文件和5脚本，共239528路径前后冻结。无发布、推送或ROM分发。本包完成后停止。
