#!/usr/bin/env python3
"""Write the phase3 narrative using the final retained validation receipts."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from source.recovered.game_enums import TACTIC_NAMES,TACTIC_ACTION_COSTS
from source.recovered.battle import TACTIC_ENTRY_POINTS

def main():
    verification=json.loads((ROOT/'analysis/phase3/verification.json').read_text())
    names={'battle_fsm':'战斗','attack_fsm':'普通攻击场景','duel_fsm':'单挑'}
    rows=[]
    for c in verification['controllers']:
        rows.append(f"| {names[c['area']]} | {c['main_states']} | {c['entry_case_count']} | {c['semantic_case_count']} | {c['executed_ir_instructions']} / {c['lifted_ir_instructions']} |")
    tactics='\n'.join(f'| {i} | {name} | {TACTIC_ACTION_COSTS[i]} | bank12 `${TACTIC_ENTRY_POINTS[i]:04X}` |' for i,name in enumerate(TACTIC_NAMES))
    text='''# 第三轮：战斗、普通攻击、单挑状态机与可读源码

本轮补全了 **三台有边界状态控制器的全部合法分派、条件路径和状态写入**，并整合进共享 RAM/SRAM 的 Python 源码。战斗胜败、换边/回合、城市归属/首将修复、战损/军粮资金归还、单挑体力写回与返回战场另有可读的高层函数。

入口：[交互状态机浏览器](index.html)、[源码说明](../../source/README.md)、[联合验证](verification.json)。原ROM全程未修改，重建文件仍逐字节一致；SHA-256为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

## 三台控制器及真实连接

| 控制器 | 状态字段 | NMI场景 | 物理bank / CPU入口 | 合法主/子组合 |
|---|---|---:|---|---:|
| 战斗地图 | `$0500/$0501` | 3 | 12/13，`$A028` | 101：98个本地组合及state15在bank8的额外3个结算子状态 |
| 普通攻击场景 | `$0540/$0541` | 4 | 14/15，`$A069` | 58，56个不同子入口 |
| 单挑 | `$04A8/$04A9` | 5 | 23/24，`$B100` | 116展开组合，92个不同子入口；主10/11/12是初始化别名 |

普通攻击表实际只有 **11项**，结束于`$A084`，后面`$A085`立即是代码；单挑22项结束于`$B143`，后面`$B144`是代码。没有凭位掩码或线性反汇编添加虚构状态。

`$0078`是NMI场景选择，`$007A`是另一层全局主循环状态。固定bank31先完成场景初始化，再由NMI调度控制器。源码 `game_engine.py` 路由三台控制器，global初始化、PPU/NMI前序与音频仍有独立依赖。

```mermaid
flowchart TD
    B["战斗：0500 / 0501，NMI3"] -->|"确认攻击，007A=5"| SA["全局E22F：设置NMI4"]
    SA --> A["普通攻击：0540 / 0541"]
    A -->|"主状态5，007A=7"| SD["全局E2E8：设置NMI5"]
    SD --> D["单挑：04A8 / 04A9"]
    D -->|"结算，battle=11/0，007A=3"| SB["全局E18B：设置NMI3"]
    A -->|"主状态4返回，007A=3"| SB
    SB --> B
    B -->|"战后state15结算，007A=1"| C["城市控制：0400=13，0401=0"]
```

控制图与各状态的条件/写入/依赖详见 [战斗目录](../battle_fsm/all-entries.md)、[战斗说明](../battle_fsm/README.md)、[攻击场景说明](../attack_fsm/README.md)、[单挑逐状态目录](../duel_fsm/handlers.md)、[单挑说明](../duel_fsm/README.md)。原指令及包含iNES头的文件偏移都保留在对应 `.asm` 与JSON中。

整合层要求显式提供控制入口的 `$8000` 数据银行。三份保留快照执行原NMI到入口均观察physical bank2，而RAM `$DE` 保存的是restore bank6，两者不能混用；[入口上下文验证](game-engine-context-validation.json)记录了确切步骤和映射。`tick_scene()`本身不执行完整NMI前序，调用者仍需准备OAM/队列条件。

## 状态与字段的新结论

- 战斗菜单二维索引依次是移動→4、攻撃→3、計略→5、待機→7、退却→6。普通攻击相邻目标与确认在主2/3；单挑经攻击场景主5进入。
- 单挑普通攻击确认阶段就执行双方体力写回：按slot0再slot1。两ID同址时后写覆盖前写。体力归零会结束/分派败北流程，但这次写回自身不改武将状态低2位，不能统一叫永久死亡。
- 单挑结尾将battle置11/0并写global3；battle11处理升级/武力变化提示。经验增量出现在交回战斗后的处理，不能把后续增量都归到单挑本体。
- `$063C[单位槽]` 已确认是 **低10位兵数÷100缓存**，空槽写FF。移动成本的两张表由其是否≥6选择，正常域对应兵数是否≥600；这是兵量档，与武将byte11的平/山/水适性一起索引成本。
- byte9上6位在初始237记录中均0。UI和兵损只读低10位，兵损即使为0也清掉上6位；AI排序及部分条件读原始word/高byte。因此保留raw16和masked10两种视图，没有擅自将高位命名成独立状态flag。
- byte5在未入名册流程写城市位置；状态0/1/2/3的名册/出场/移除行为已列出。状态3是否永久死亡仍须按路径区分，战斗结果码0515/0517也与武将状态位分开。

## 16个计略名称及绑定

名称来自原CHR字形，并通过 `$0580[菜单行] → $0543 → $B02B` 执行表直接绑定。完整模拟器自然出征的曹操菜单可见前10项；另6项保留原字形、记录指针与packet/分派对照。

| ID | 原字形名称 | 行动成本 | 效果入口 |
|---:|---|---:|---|
TACTICS

计略名称已接到 `game_enums.py`、`battle.py` 与AI结果的 `chosen_tactic_name`。完整计略条件/效果控制路径在battle IR中保留；名字与执行入口绑定不替代每一计略完整PPU效果验证。

## 地形的确认范围

raw类别0森林、2平地、3水域、4山地、5城/城砦与原renderer像素对齐，报告把这些标为有依据的外观标签。类别1目前只能确认平滑橙色地面，其正式名称未恢复；原类别6/7/8名称也未恢复，AI均将≥6折为2。

地图四象限的120个chunk指针/银行、tile→class查找、移动成本都已对照原指令。32×32提取数组含属性及未用行；有效battle坐标x<31、y<20，y15为属性行，绘图y≥16先减1。不得把全部1024项叫可行走格。

武将地形适性0平/1山/2水有真实移动成本作用；原编码3第四列为0并越过三项字形表读取指令字节，未当成第四种合法能力。详见 [名称/地形/剩余字段报告](../names_terrain/README.md) 和 [字节/像素证据](../names_terrain/evidence.json)。

## 源码层次与验证

`battle_state_machine.py`、`attack_state_machine.py`、`duel_state_machine.py` 执行提升后的IR，包含真实条件、ALU、flags、栈和RAM写入；它们不从原ROM取控制指令，也不以原ROM入口stub替换状态体。控制层保留机器级形式以免丢失边界行为；高层语义、数据字段、名称/地形及整合层另用普通函数/类表达。

| 控制器 | 主状态数 | 全入口fixture数 | 高层语义fixture数 | 动态执行IR / 静态IR |
|---|---:|---:|---:|---:|
ROWS

所有上述fixture通过。战斗另有56次主入口tick及4,096次新增8个固定helper直接入口对照；单挑另有72次同址/边界HP写回及3条连续构造序列；攻击场景另有75次全分派指针检查。全部合法入口覆盖不等于所有条件分支都实际执行过，表中保留动态指令覆盖的真实分母。

名称/地形/剩余字段 **NAMECASES** 次原指令对照通过；6个固定银行控制/寻址/RNG源码入口 **SHAREDCASES** 次对照通过，比较寄存器、flags、zero-page及stack。REA新增pair23/24加载 attestation为verified，导出124个候选函数；五组银行对累计511个候选函数，Ghidra伪代码仍须按内联表/跨银行约定校正。

控制器验证中的未恢复helper使用明确的实际ROM adapter；battle `$ECEE` NMI等待屏障在CPU两侧明确跳过。因此测试证明该范围的控制/内存行为一致，不能说所有外部helper已独立复原。共享源另有高层算术、胜败和结算函数；剩余依赖按地址及影响状态列在各报告。

## 完整NES核心的两类证据

**自然原ROM流程：**7,738帧冷启动→选曹操/兗州→軍事→侵略→出兵→战斗→计略菜单。无ROM改动、无RAM注入；输入计划是 [replay-cold-to-battle.json](../runtime/phase3/replay-cold-to-battle.json)。9个检查点的画面和SRAM一致，CPU RAM有8–26字节差异，未隐去或称全状态一致。观察到的战斗状态覆盖0/4/5/10的一部分子流程。

**明确注入的单挑集成fixture：**完整Nestopia核心执行1,025帧，观察0→9→1→16→19→3→13→14及返回battle11/0/global3→4。双方永久体力80/5→74/5→74/0；两次40个非空pixel/RAM/SRAM/core.state快照一致。测试注入原父场景的双方ID、体力及控制参数，`natural_gameplay=false`，不能当自然可达性证明。VRAM libretro区域不可用、导出0B，已排除；图像和core.state仍由真实核心生成。

普通攻击场景也有受控相邻敌人fixture：只把敌slot0的坐标从(20,14)改为(3,16)，由原battle代码准备攻击参数，实际NMI4显示阵形选择、双方兵士动画和统计。证据位于 `analysis/runtime/phase3/injected-adjacent-attack/`，没有把它称为自然出征流程。类别1地形的受控renderer fixture也单独标注。

![自然出征的计略菜单](../runtime/phase3/battle-tactics-true.png)
![单挑集成fixture，明确RAM注入](../duel_fsm/runtime/injected-core/fixture-state-16.png)

## 复现与当前边界

```sh
python3 scripts/game_engine_demo.py
.venv-trace/bin/python scripts/verify_battle_fsm.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_attack_fsm.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_duel_fsm.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_names_terrain.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_controller_helpers.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/verify_phase3.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

仍未完整独立复原的是部分renderer/文本/俘虏政治helper、全局内政/战役、音频及少量正式字段名称。C11库是计算部分，Python控制层也要求显式依赖；本轮没有宣称得到原作者源码或独立可运行的全游戏重制。原始字节已全部保留，可一致重建，并与新增源码、报告和证据一起归档。
'''.replace('TACTICS',tactics).replace('ROWS','\n'.join(rows)).replace('NAMECASES',f"{verification['names_terrain_cases']:,}").replace('SHAREDCASES',f"{verification['shared_helper_cases']:,}")
    (ROOT/'analysis/phase3/README.md').write_text(text)
    print('Wrote phase3 report from final scope-specific verification')

if __name__=='__main__':main()
