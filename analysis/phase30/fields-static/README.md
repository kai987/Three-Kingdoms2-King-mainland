# CC29完整姓名指针：两个条件不交合同

本轮只迁移13:CC92、CCAC两处，冻结1526分母由1198/81/247变为1200条件不交/81可能/245未知，328候选→326。城市+1/+28..31正式含义仍未知；条件不交不是所有裸入口、所有CPU总线或全ROM未使用证明。

完整CC29先F25F31选physical17，再以0507高/低ruler索引经F368取首将byte。合同限正常ruler0..6，保留全部rawleader0..255；237..255超出已识别237条姓名表但不能截断原算法。EBE9真乘13、完整加8DB4后CC92以Y0读首byte，原12次CCAA/CCDF读后12byte。原指针域8DB4..9AB3仍在ROM窗。所有postconstructor写已盘点：只有CCDF递增06/07，OAM绝对X写0200..0302不触指针。无中断前提明确，不把瞬间低半更新称为硬件原子，也不按同callPC关联不同动态代。

 CC6D本身不选择data bank；其直接矩阵为显式选bank17的typed构造caller，不能泛化为所有裸CC6D。原完整CC29矩阵从另一data页开始，实际执行F25F。每个正常ruler覆盖全部256个当前leader和两方次序；另一方取固定循环ruler及rawleader置换，并非穷举全部双leader笛卡尔组合。结构证明按当前单包因子化：构造前重设00..03，乘法重设04..09，前一包不改ruler SRAM；因此不能仅用采样量代替完整写域／调用链依据。裸CCAA以06/07=6001/601C/601F真实读辅助字节的三个前缀反例保留；rawruler7..15只执行F368前缀后在CC72前停止，8的5F20硬件值没有伪造。

新增独立原CPU合同7188案：7172正常RTS、16明确前缀；其中冻结29软件输入8份重新CPU续行（CC29四完整RTS，D4F0四案仅到D4F3），不是新Native捕获或Source对照。模型/字节检查21项单列。生产Source病例0、Native帧0。全部固定helper执行原指令，无helperRTS替身；Bus只含2K RAM/8K SRAM/PRG和真实mapper写，其余硬件读拒绝。逐案核所有8K SRAM不变、读取顺序与完整地址域；没有假称对另一Source全2K/寄存器差分。

逻辑EA与dummy分开。这里两种IndY读均Y0，没有额外跨页dummy读；py65仍不是完整微周期总线观察核。raw345账本逐项继承104操作数/13数据/228未证控制，不增加动态覆盖或未使用名称。

复现：`python3 scripts/analyze_unknown_pointer_phase30.py ROM`；`.venv-trace/bin/python scripts/verify_unknown_pointer_phase30.py ROM`。仅写新phase30目录，不运行旧producer，旧Source/Native/归档不改。
