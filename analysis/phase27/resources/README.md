# G106战后城市资源精确服务

PostbattleResourceServices(DeploymentPointerServices)仅新增BF0A/BF9E/BFB3/BFEC四个真实caller入口。既有battle_state_machine.postbattle_city_losses已经具名恢复算术；本轮新增可读register/scratch/栈/mapper协议118个原指令位置267B、18B表，不称首次发现资源损失算法。A006/BAB3及BB93 ECEE完整父层仍缺精确owner。

BF0A只在0514==0继续；非零原RTS。通过F25F raw30→physical16更新E1数据窗（不是主线程DE），F2AF以050E原始byte构造6000+32×rawcity并完整复制00/01到1A/B。E87A采样低位决定字段6损失率1或2；0506按6/11/16/21分组给字段8、14和byte11损失率1/2/3/4/6；字段2/4从BFEC选择率。四次BF9E JSR与BF9B尾跳都保持原caller帧，实际输入中尾跳返回BB99。

缩放保留原byte factor=(10−rate)&FF、乘积只取低16位后除10。byte11只回写低byte；其他字段先低后高，Y按byte增加。每次访问重取live1A/B，不能缓存旧pointer：裸001A、001B、081A与scratch02等alias可改变第二次写地址/值，已独立对照。裸helper没有完整BF0A的字段资格，不能从完整链无辅助字段写推导其任意Y都安全。原BFEC的递增阈值表501/1000/3000/5000与BCC意味着本入口输出实际只有rate9或5；不是按常见分段规则修正成五档。

Source对照3197父case：{"actual_caller_RTS": 3194, "strict_missing_dependency_prefix": 3}，另7guards。完整2048RAM含闲置栈、8192SRAM、AXYP-SP-PC、四银行、combined logical IO读写交织、共同明示N163均比较；Source原CPUcallbacks0，无IR执行或fakeack。动态覆盖本域118/118原位置；计数不与Rootfrontdoor或原CPU静态合同重复。

10实际软件现场见../cpu-resource：1自然退却、9受控祖先positive，保留19已知准备和更早phase3未完全建立的准备范围。N163不是瞬间捕获，另给共同设备夹具。原机两路线实际15逻辑读、11写及11个STA dummy读取由独立被动核观察；py65只逻辑读取/写入，不发dummy。

静态合同仅完整BF0A producer、binary/no-interrupt normalreturn有效；7点逻辑地址与dummy分表，保留rawcity及裸alias。正式+1/+28..31名称仍未知；本链无逻辑命中不构成全ROM未使用证明。

复现：.venv-trace/bin/python scripts/analyze_postbattle_resource_services.py ROM --import-native-callees --import-only；scripts/verify_postbattle_resource_services.py ROM；scripts/analyze_postbattle_resource_services.py ROM --evidence-only；scripts/analyze_unknown_pointer_phase27.py ROM；scripts/verify_unknown_pointer_phase27.py ROM。所有脚本仅写phase27。
