# 战后释放与分配的具名源码

[PostbattleReleaseController](../../../source/recovered/postbattle_release_services.py) 手写恢复 physical13 `D1F9..D2CC` 的212B/106个原指令位置：选中武将逐一处理、普通城市分配、特殊目的地30释放、六个active数组或俘虏表清除。它继承冻结BattleSceneController，只替换`local_d1f9/local_d20d`绑定；真实主13/14父流程保持原JSR栈。生产没有ROM执行、IR或CPU fallback。

`D1F9`遍历0580的20个标记，所有非负值都表示选中。`D20D`在0540==30时保留status高6位、清低2位，再用原E856和bank16邻城表选择所在地；负邻城则用原战斗城050E。它不检查或改HP、兵数、忠诚。接着`D299`先找20个active ID的首个相等项，清六数组；没有则找连续40个俘虏ID并仅清首项，不删除城市名册。

普通目的城也完整具名编排：复用原BC11的城市指针和首FF，追加ID、必要时更新052C首将目的地；原中立owner使用`(owner&F0)|side_ruler_low4`，保留F0掩码，不能简化成F8。父UI负责真实城市容量、不可释放君主和选中行资格，直接D20D入口不重新伪造这些资格。所有固定服务保留真实调用帧；没有自动text/IRQ/NMI ready。

当前1370个原CPU父例：1365 RTS、3非局部返回、2严格依赖前缀；另5 guards，全部通过。比较完整2048B RAM、8192B SRAM、AXYP/SP/PC、有序IO、四PRG银行与N163状态，无自由栈排除。新106/106位置动态命中，但不代表全部输入或路径。域计数：`{"controlled_numeric_and_caller_CPU_fixture": 1360, "strict_missing_dependency_fixture": 2, "Native_snapshot_plus_declared_hardware_NMI_CPU_fixture": 3, "actual_Native_snapshot_originalCPU_reached_caller": 5}`。

1362个数值/软件caller矩阵是明确CPU fixture。正式保存点导出的pure continuation与显式硬件NMI释放夹具按origin分别记录；后者只在CPU模型安排一次真实NMI栈协议和A端口输入，不是Native内部callee寄存器录制。新22矩阵也复验冻结21录用源码在实际成功输入下的完整父返回/双PLA非局部返回，不改21任何文件。

```python
controller = PostbattleReleaseController(memory, rom, services=readable_services)
controller.run_entry(0xD1F9, registers=actual_caller_registers)
# 主A000/A028仍通过原父调用方法绑定进入新具名函数。
```

```sh
.venv-trace/bin/python scripts/verify_postbattle_release_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_postbattle_release_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[原字节](original.asm) · [静态目录](static-catalog.json) · [差分](validation.json) · [证据](evidence.json) · [status0生产者目录](../producers/catalog.json) · [原机路线](../runtime/README.md)
