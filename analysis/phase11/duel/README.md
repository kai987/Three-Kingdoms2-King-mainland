# Phase11 单挑场景控制器

`DuelSceneController`是从固定原bytes静态恢复的具名、结构化Python控制源码：22主态、116合法主/phase组合、92个distinctphase入口、19个原指针分派表及136局部函数。编译期分析原CFG，运行时只执行普通Python if/while和具名call；不读program.json，不解释opcode/PC指令字典，不调用旧DuelMachine/IR或原CPUfallback。源码中 `_mark` 是原地址追踪，服务入口whitelist用于具名routine调用，不是指令执行器。

B11F在B118..B143主pointer DATA中，不能当初始化代码。state0 driver B144、phase0 B15A，等待真实0087 bit7，读两条永久record体力和装备分类。CDFD完整构造5×8tile BG行请求：原index*40+D2AB数据、地址低/高carry、55个command字节与FF终止、007E|4。CEA5按参数bit7映射physical20/21及真实sprite pointer；CEE1保持原计时、上下起伏、声音请求/返回寄存器副作用；CFA3按13B名称图记录构造命令。D060..D2AA包括真实HP写回/健康条、按钮提示、武将panel/菜单/配对白/君主和queue完成判断，均为局部source。构造请求不等于PPU完成。

| 主态 | 原入口 | 合法phase | 具名作用 |
|---:|---|---|---|
| 0 | `$B144` | 0..7 | 读取记录及初始化场景 |
| 1 | `$B34F` | 0..5 | 轮换行动者与玩家/电脑入口 |
| 2 | `$B5C8` | 0..4 | 电脑动作选择 |
| 3 | `$B8C7` | 0..2 | 普通扣体及确认写回 |
| 4 | `$BA6D` | 0..9 | 退却、追击与永久体力扣减 |
| 5 | `$BC3B` | 0..2 | 显示双方武将资料 |
| 6 | `$BCE9` | 0..5 | 投降结果动画 |
| 7 | `$BE78` | 0..3 | 説得候选结果 |
| 8 | `$C08A` | 0..0 | 罵倒及04B5持续状态 |
| 9 | `$C116` | 0..3 | 双方对白及控制回调 |
| 10 | `$B144` | 0..7 | 初始化别名0 |
| 11 | `$B144` | 0..7 | 初始化别名0 |
| 12 | `$B144` | 0..7 | 初始化别名0 |
| 13 | `$C21C` | 0..3 | 零体力表现 |
| 14 | `$C2F6` | 0..3 | 结果与装备奖励、回战斗 |
| 15 | `$C464` | 0..1 | 结果淡出、回普通攻击场景 |
| 16 | `$C498` | 0..6 | 动作类别0移动表现 |
| 17 | `$C689` | 0..7 | 动作类别2移动表现 |
| 18 | `$C949` | 0..7 | 动作类别6移动表现 |
| 19 | `$CB9E` | 0..2 | 移动归位与恢复保存状态 |
| 20 | `$CC87` | 0..2 | 向外移动及恢复状态 |
| 21 | `$CD3C` | 0..2 | 向内移动及恢复状态 |

actor04AA=0/1；main04A8、phase04A9；04AD/AE两officerID，04B1/B2临时体力，04BF动作类别，04BD/BE是不同主态里的保存目标/对白/结果索引。主菜单正式字形及原数字见既有DuelLogic.ACTION_NAMES。D060先写side0后side1，ID相同则side1覆盖；两体力条仍按临时数组分别构造。零体力result2、退却/投降/説得的0515/17是战场结果码；它们不是武将byte11 status，也不能在这里推断永久死亡/城市名册删除。main14/sub1等待真实fade后写battle0500=11/sub0、global7A=3；main15/sub1写global7A=5回普通攻击显示，均依赖真实ECBF。

本控制器直接复用冻结ControlHelpers的EADE/F2D7/RNG、AudioServices真实音频请求，以及BattleGraphicsServices.screen_sprites的真实OAM构造。`logic`保留同memory的既有DuelLogic纯规则接口与其immutable数据，controller自身的flags/scratch/stack也已恢复。额外固定queue/menu/math/fade/mapper可由根的新SceneSharedServices供给；portrait/完整officer资料等farcallee仍由明确服务owner完成，不装原CPUfallback，也不空完成文本/绘制。

```python
controller = DuelSceneController(memory, DuelSceneData.from_rom(rom), services=services)
result = controller.tick(registers=actual_caller_registers)
# result.status==dependency 时提供真正完成的服务，再controller.resume()
```

services使用ServiceCall(target,return_pc,kind,registers,memory,entry_banks,expected_sp)。源码实际保留JSR、EADE和inline farword帧；EE07回PC+5，外部回调必须恢复真实returnPC和SP。单纯返回status='returned'而没恢复PC/SP会停dependency。源码不植入0200，也不种假RTS；本函数自己的真实RTS消费caller帧，根NMI23A01B→B100 bridge继续保持原协议。没有服务、消息/绘制尚待处理、或服务owner未恢复都不会伪装完成。source运行budget是显式异常，不是伪造帧/ack。

最终6044个原CPU用例、另4个源码guards，0失败。全部局部入口、22态每个合法phase、21个关键timer边界/双方motion端点、HP0/1/9/10/99/100和同record覆盖、奖励特殊身份/flag/alias/RNG，以及216个説得表格均检查。全部1856声明RAM（非栈、真实palette100..13F）、8KiB SRAM、AXYP/SP/PC、mapper和写端口顺序对照。fixture沿既有受控duelcore snapshot，明确注入演员/阶段/记录/按键/队列/fade flag：这是CPU条件矩阵，不是自然游戏输入或真实PPU已完成的证明；原ROM始终只读。根线程另行原核心回放证明真实按键/等待路径。

外部原CPUhelper仅安装在verify脚本，4846次真实调用按target单列在回执；每次必须到真实returnPC/SP，源码运行不包含此adapter。另组合矩阵用新SceneSharedServices的独立Python固定helper，916次源服务真实执行；其中未恢复farcallee仍单列验证CPU，不隐藏为生产纯源码。服务当前已恢复范围与未恢复farcallee是不同覆盖层。动态观察3077/3316个本地原指令位置，未观察位置在evidence逐项列出；不称所有值域/分支或完整NES帧均验证。空闲CPUstack残留、硬件时间、PCM合成均不在比较合同。

- [独立源码](../../../source/recovered/duel_scene_controller.py)
- [冻结CPU回执与三项pins](validation.json)
- [完整bytes/表/依赖与状态目录](evidence.json)
- [原代码及明确DATA反汇编](original-ranges.asm)
- [静态结构与无gap结论](static-control.json)
- [实际原CPU指令位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_duel_scene_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_duel_scene_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence
```

重新生成source用`--generate`，它只是buildtime decompilation步骤；编辑/重生后必须重跑validator再冻结pins。旧源码/旧IR文件没有修改。
