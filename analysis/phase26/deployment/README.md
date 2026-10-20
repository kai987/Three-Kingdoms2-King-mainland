# G107部署坐标指针

新增DeploymentPointerServices(BattleSetupAI)，仅把既有直接源码中仍是通用控制形态的B2AE/B312两体重构为可读流程：92个原位置/187B。B1B0的profile/strategy分组与四坐标读取继承不变；不重复称首次恢复部署算法。新增证据是完整caller/栈/mapper合同与四个完整指针读地址合同。旧phase11只有1972RAM排除free-stack的2326例，本轮不同scope单列。

PUBLIC五入口A003/B130/B1B0/B2AE/B312要求真实registers.pc、physical8/9窗口及已有返回帧；拒绝seed_return和错误PC/SP返回。缺F266保留真实pending。Source不执行CPU、IR、opcode字典或动态代码生成。

first：F266 raw30→physical16查邻城；match时raw31→17查template，negative sentinel则0；byte offset=32×template mod256；raw26→physical6，以(2×city)&FF完整取8C52表word加offset。second：raw30→16查9E62，offset是原ASL4+ADC原值+ASL，即34×template mod256，最后raw26→6取8000表word。先前口头36不是原ROM算术；冻结旧报告不改。

20/21先是profile/work，再完整重建为坐标指针；22..25为独立组游标。B272/B278读commanderY0/1，B290/B296按strategy组offset读成对坐标并推进该组2。正常city0..29读bank6 ROM；raw0..255完整保留，30..127/158..255可能指内部RAM镜像。保守second raw域极端Y触及2000..200E，这些只有地址合同，未给硬件输入不能称读取成功/无副作用或正常玩法。裸四读不获得完整构造合同。LDA的额外dummy只在跨页时存在，py65只加周期不模拟该读；和STA无条件dummy分开。

Source完整对照2009个父case，分类{"actual_caller_RTS": 2007, "strict_missing_dependency_prefix": 2}，另7guards。完整2048RAM含闲置栈、8192SRAM、AXYP/SP/PC、真实四银行、读写交织的combined logical IO及N163共同fixture均比较。无新增IRQ/NMI或fakeack。原CPU静态/地址合同、Root统一工厂和Native帧分别计数，不能相加称全ROM完成。

本轮Native只实捕first formation；B312仅Source/原CPU合同覆盖，不能声称原机两侧都走过。三份被动软件现场见../cpu-deployment；N163未现场捕获，明示共同fixture。runtime原/新核心同路线五buffer相同不构成全局等价定理。

复现：.venv-trace/bin/python scripts/analyze_deployment_pointer_phase26.py ROM --import-native-callees；verify_deployment_pointer_phase26.py ROM；analyze_deployment_pointer_phase26.py ROM --evidence-only；analyze_unknown_pointer_phase26.py ROM；verify_unknown_pointer_phase26.py ROM。
