# G033完整指针与映射合同

仅将physical11 C61F/C624两处逻辑读从未知排除：本轮前unknown260→258；全1526条分类为1187不交、81可能、258未知，候选341→339。55组/270访问是第23阶段原unknown分组经第24阶段保留的历史成员，不是本轮前unknown总数。本轮只比较G107与G033并选择G033，不宣称重新恢复全部55组。

完整14条前序C5F8..C614包含真实D471乘法JSR，must-builder要求完整进入、同一前序所有边都通过；bypass join或裸高字节store不制造完整指针。19条D471用原bytes+全部rawcity×20原CPU合同核对。循环侧域保留所有Y byte；没有凭FF或10pair假设终止。所有256原city字节含30..255都保留，后者只是机器域，不称合法城市。

22/23=8B1C+20*rawcity。合法城市0..29即使所有Y0..255，逻辑读仍在银行17 ROM；raw255+Y248..255逻辑A000..A007由银行10代码窗提供，而同次IndY未进位dummy页为9F00..9F07、银行17。逻辑EA与dummy bus分别重算。该结论仅两条读，不替整个C5D2所有写排除城市辅助字段。

mapping-lifetime-contract.json从C5D2闭包252个原位置列完整callee/写入。入口真实LDY49/F266选择17，setter与指针高byte完成均支配两读；仅F269直接写PRG端口。中间typed city cap和officer status写不碰ZP/stack/mapper。C66C裸/raw无界append仍保留：它后面直接RTS而不再访问两表读，不能用此证明append安全。普通无中断、二进制算术、完整caller合同之外的任意裸输入/IRQ/NMI/外部内存写不被接纳。

verification.json中的33280个原CPU合同与Source差分另计：256个D471真实软件帧RTS、256个完整构造prefix、32768个偶/奇pair读取prefix。后两类不是完整C5D2返回，更不是Native帧。自然被动caller及实际映射见../cpu-appearance，Source helper与统一factory对照见../appearance及../source-integration.json。

城市+1/+28..31正式名称仍未知；ROM表读取并不赋予城市字段语义。零值、有限路径未写或裸alias不构成unused/padding/bug的结论。

## IndY_R候选地址与实际额外读取

每条pair_read_checks访问的candidate_not_actual_dummy_address只是未进位地址公式。只有page_cross_dummy_read_required=true时，官方核心IndY_R才执行额外读，actual_dummy_bus_address才非null；未跨页没有额外dummy（如rawcity0/Y0）。raw255/Y248..255确实跨页，因此9F00..9F07额外读取成立。py65只增加跨页周期，不调用该dummy内存读；验证器对既有矩阵10条指令记录实际py65读序，不能将公式冒称观察到的总线事件。原Native配兵提交STA的无条件dummy读取是另一种IndY_W规则，与此处LDA的条件读取分开。
