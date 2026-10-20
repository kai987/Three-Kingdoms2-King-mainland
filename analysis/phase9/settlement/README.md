# Phase9 玩家结果与升级通知来源证据

本目录固定原ROM的8段结算字节、源码及验证器SHA。生成器只读取文件、做静态反汇编与AST/哈希核对，不执行ROM、IR、CPU、游戏帧或玩法公式。它没有新增原CPU病例；引用现有集成回执的1421项原CPU比较、12项原核心field比较与3项源码guard时，各范围仍按该回执区分。

| 范围 | 物理bank | CPU闭区间 | 文件偏移 | 字节数 |
|---|---:|---|---|---:|
| player_scan_and_message_selection | 12 | AAA7..AB19 | 0x018AB7 | 115 |
| player_result_message_table | 12 | AB1A..AB29 | 0x018B2A | 16 |
| player_confirmation_and_notifications | 12 | AB2A..ABA3 | 0x018B3A | 122 |
| level_change_query | 13 | DEE9..DF26 | 0x01BEF9 | 62 |
| second_notice_trampoline | 8 | A018..A01A | 0x010028 | 3 |
| second_notice_officer_gate | 9 | D390..D3D7 | 0x0133A0 | 72 |
| second_notice_officer_table | 9 | D3D8..D3ED | 0x0133E8 | 22 |
| sixteen_effect_reset_and_dispatch | 12 | B02B..B061 | 0x01903B | 55 |

合计467原字节：393代码字节、74数据字节；169条静态解码指令，不代表动态覆盖。`evidence.json`每段包含完整rawbytes、SHA、代码/数据分段及源码方法行号，`original-ranges.asm`逐地址显示文件偏移。完整段覆盖与段内跳转落点均实际检查。

AAA7先读真实007E。050B是结果扫描cursor，复制至0509，实际D6CC返回后才递增，20槽扫描完推进子状态并排结果消息。失败用73/job2；成功按16项AB1A表取消息。ID9无兵损按ID1文字处理，ID1/9有死者0432则用4E/job5。队列写入不等于原消息已完成。

AB2A/AB52分别调用真实DF27、DC63后检查0081 bit0。AB41调用DEE9查询已发生等级变化；改级时推进子状态，并交实际E57F/E68B音频。第二通知读042D，未用过时先置FF再排4B/job5；下一次真实A确认交E57F/E673，然后AB6F复制046C..046F到6F3F..6F42、清0500/0501，交A1F7光标绘制。源码的具名after_*合同只从实际前序服务已返回的位置继续，不默认完成服务。

内联数据精确为AAE0的A027（EE07 selector3D→29/30）和DF15的A018（selector28→8/9）。它们不是指令。B03F的EADE后B042..B061是16项LE16效果入口；AB1A..AB29是16个消息byte；D3D8..D3ED是22个通知tablebyte。三者均标数据，避免把表中6C误读成JMP或把inline18误读成CLC。

实际链为bank12 AB41→bank13 DEE9→fixed EE07(selector28、inlineA018)→bank8 A018 JMP→bank9 D390。D390用record11高4位：level3/4/5/6起点0/11/17/20，均扫描**同一个末FF终止的尾列表**。其作用仅决定042D第二通知标记，不发装备、不改名册、不在本段授予新计略；真实可见新计略文字属于消息说明，原玩法能力读取另有等级规则。

AB90..ABA3另有相邻确认handler：真实DF27/DC63和A通过后清0501，其余RTS。该块已附原bytes，当前统一高层源码和集成验证器没有对应方法/测试，明确记作original-only，不能据同一个大范围的存在声称已经高层化。

当前固定统一源码SHA `b57e3551164ce07988262a001f8ef772ecac41ca631e8eac979f3e07f0fb7d14`；验证器SHA `62cbb4f12d965ab8618accb2340beeec711f12f814d2095b944c32a7a7d6ce2b`。源码ROM切片经AST核对精确对应16消息表与22通知表，并与现有CPU回执sourcepin一致。外部图形、音频、readiness与完整NMI仍按真实边界说明。

- [可机核全部证据与pins](evidence.json)
- [原字节反汇编及数据表](original-ranges.asm)
- [当前统一结算源码](../../../source/recovered/tactical_effects_complete.py)
- [当前原CPU集成验证器](../../../scripts/verify_phase9_integration.py)
- [引用集成回执](../source-integration.json)
- [正式原核心实验](../runtime/README.md)

```sh
python3 scripts/analyze_phase9_settlement.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
