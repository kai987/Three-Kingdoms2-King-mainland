# G107：父入口、当前owner与完成边界

本目录是只读上下文核查，新Source病例、原CPU病例、Native运行数均为0。冻结25前门AppearancePointerGameEngine/Coordinator对8/9继续路由到BattleSetupAI；新26前门DeploymentPointerGameEngine/Coordinator只接管A003/B130/B1B0/B2AE/B312五个入口，由DeploymentPointerServices负责，继承25其它owner。此处是静态路由核查，不预先声明新Source执行已通过。B1B0、B2AE、B312已分别是assign_strategies_and_positions、first_side_formation、second_side_formation；后两者是父owner内的局部JSR，不能算新发现的三个缺失服务。

原全局链为E18B→0500!=11→LDY#28(十进制40)/F237→physical8/9的A003→B130→每侧ruler记录byte3==3门→B16B/B195调B1B0→B25D/B263调B2AE/B312。0500==11走12A006单挑后果分支，不能把所有E18B完成都视为G107命中。E18B最终到E066主循环边界，不是普通caller RTS。

现有自然supply-third母状态是普通A续行的合理起点；旧handoff-011的300000指令无中断CPU负probe可能已在初始化之后，只能说该保存点/预算未再命中，不能证明G107不可达。Native保存点后独立CPU续行不是固定原核内部捕获；新26被动opcode捕获和设备夹具仍须由自己的回执说明。

更正仅在本轮说明：冻结11README/25comparison所写第二侧36B不符原算式。原代码四次ASL得到16×，加原index得17×，再ASL得34×；offset保留8位回绕。第一侧五次ASL是32×。这是旧文档的更正，不是新算法发现，不修改旧文件。

稳定静态分母是G107四处B272/B278/B290/B296，归于全部1526项；25基线1187不交/81可能/258未知，剩339。上下文审计本身新增排除0，不预写26最终数。旧799位置/19过程是整个setup/NMI辅助模块，不能重计为26首次恢复；旧2326CPU/1972RAM及自由栈排除保持历史范围。新Source若改为全2048真实caller比较，是新增协议/范围证据，应另列。

normal RTS必须有真实caller、statusreturned与真实PC/SP同时匹配。waiting/dependency保持pending、strictprefix只证明前缀；nonlocal、reset和globalE066边界单列。不能人工ack、伪造栈，或把外层frameend银行当即时ROM坐标读银行。第一侧32×与第二侧34×(均按原8位offset算式)模板、rawbyte和裸alias域保持区分；不凭有限负观测给城市+1/+28..31命名。

owner-and-caller-chain.json保留原字节与含16B头偏移、真实局部JSR关系、旧证据定位；completion-contracts.json列mapper/caller前提；stable-denominators.json与acceptance-delta-framework.json给十维收口框架。新26 Source、Native和Root整合仍由各自回执验收，本目录不运行它们。
