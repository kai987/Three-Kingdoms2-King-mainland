# 阶段31玩家战后处置的既有源码对照

本轮未新增生产Source owner。现有 BattleSceneController 的 main13（CD16）/main14（D2CD）各7子态、phase22 PostbattleReleaseController 的 D1F9/D20D，以及 phase30 PostbattleEarlyGameEngine/SceneCoordinator 已覆盖此声明调用范围。既有玩法、指令具名和精确早态协议各保留原信用，不称首次恢复。

main13/14 的真实阶段表、原字节、Source函数与行号见 static-catalog.json。文本只在0304和0300都等于FF时允许确认；只新A位1推进，B/无输入或busy可正常RTS。菜单阶段由ED1E宽2选目标，ED23宽3选武将；坐标来自真实游标，不能直接伪写已选结果。确认经CF2D→D1F9→CF30或D486→D1F9→D489，之后重建phase0。空败方名单或胜方≤10名可返回15；15D4F0先画CC29、D4F3 LDY28、D4F5真实EE07(A006)到D4FA，再返回原caller。EE07只恢复代码pair12/13，E1数据窗副作用保留。

Source CPU对照 325 案：{"actual_caller_RTS": 317, "strict_dependency_prefix": 8}；来源分组 {"new31_controlled": 192, "inherited30_BB36_controlled": 2, "inherited30_passive": 14, "new31_passive": 117}；guard 0，失败0。所有完成案比较2048RAM含栈、8192SRAM、AXYP/SP/PC、四PRG页、混合有序logicalIO及共同显式N163。原6502只在oracle侧运行，Source CPU callback=0、IR解释=0。8个缺服务prefix是主动撤去services的边界对照，不是已发现的新未知服务。

每个parent case独立克隆输入并新建GameEngine/SceneCoordinator。本回执证明逐caller软件合同，没有将这些调用串称单Source实例跨帧UI完整重放。同一原机callback可贡献wrapper/phase/leaf多个接口层病例，case数不是独立游戏路线或帧数。初始text queue/cursor/名单/按钮为明确受控夹具，不是Native ready写入。原机连续13/14→15与新被动capture由Root另供；被动现场2K/8K/实际寄存器/四银行/原栈真实，N163未瞬时捕获则仍用共同显式fixture。继承30的14现场与2个BB36受控parent另列，不称本轮新原机到达。py65无硬件dummy-cycle仿真，不宣称逐总线周期相同。

复现：`.venv-trace/bin/python scripts/verify_player_postbattle_phase31.py ROM`；随后 `.venv-trace/bin/python scripts/analyze_player_postbattle_phase31.py ROM`。只生成新31目录，不运行旧producer、不执行Native/core。本轮完成后停止，不自动启动32。
