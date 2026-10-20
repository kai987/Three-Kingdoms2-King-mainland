# G106：入口、城市指针与既有语义

本目录只读核对冻结26的frontdoor、原字节与现有回执，新增Source/CPU/Native均0。DeploymentPointerGameEngine继承的有限AST路由对physical8/9 A006/BAB3/BB93/BF0A/BF9E/BFB3/BFEC未找到明确CPU owner；这不是全程序缺失服务数量。TacticalCooperationController与DeploymentPointerServices的明确入口都不含这些地址，不能把另一bank同地址或某个syntaxexternal当作已匹配owner。

新27前门PostbattleResourceGameEngine/SceneCoordinator只对BF0A/BF9E/BFB3/BFEC四入口接新PostbattleResourceServices，26部署五入口继续旧owner。A006/BAB3/BB93未被接入，所以直callee对照即使完整返回，也不能宣称其父控制、真实ECEE或整场战斗Source已闭合。此路由表仍是静态身份核查，执行scope以新Source和Root整合自己的回执为准。

真正父链为battle bank13 D4F0 return_to_city，D4F5以selector28(hex) farcall8:A006→BAB3，按0501四word表分派。仅sub2到BB93，先调用真实ECEE屏障，BB96才调用BF0A。0514非0在BF0F立即RTS，不能把该无效果分支当成真实资源扣减；0514==0才F25F raw30→physical16，然后F2AF(050E)将完整6000+32*rawcity指针复制到1A/1B。F25F保存E1，不能沿用F266保存DE的说法。

BF9E有四个JSR caller：BF34(Y6)、BF5E(Y8)、BF69(Y14)、BF8E(Y2)，另BF9B(Y4)是尾JMP，没有额外returnframe。BF81以Y11调用BFB3单字节路径。两类入口都将原Y压到真实栈，EBE9乘法和EA7C除法后BFDA/DB恢复，BFDF写低字节；Y11跳过高字节，否则BFE9写下一字节。完整BF0A候选offset集合仅2..15中的资源字段；裸helper、损坏栈、任意1A/Y不能继承这些前提。

资源效果并非首次发现：冻结battle_state_machine.postbattle_city_losses已直接实现BF0A..C026，旧512案只比较SRAM；finalization_phase旧256案的ECEE在两侧显式bypass。GameEngine.settlement_rules是高层接口，不等于farcaller的完整CPU寄存器/栈/mapperowner。新阶段若补精确protocol是新scope，不重算整个算法恢复。六种字段是人口+6、土地+8、产业+14、统治+11、金+2、米+4，标签引用既有城市UI字段证据，不为+1/+28..31补名。

乘法先丢弃超过16bit的乘积，再除10；不要泛称所有raw输入为普通百分比。人口rate=(draw&1)+1；turn0506的rate表是1/2/3/4/6；金米原升序阈值比较方向保留，value>501用5，<=501用9。C027随后回补军粮/金，原机瞬时读写与帧末净值需要分开解释。

稳定分母1526：冻结26为1191条件不交、81可能、254未知，剩335；G106七处仍保留旧权威分类。此处完整caller候选域只用于复查链路，非新增排除，不能凭投影或有限负观测宣布字段unused。raw345保留104操作数字节/13已有数据/228未证入口。逻辑EA与6502dummy总线读各自解释；自然入口、实际bank/PC、Source对照、模型guards和字节重建都由独立正式回执说明。
