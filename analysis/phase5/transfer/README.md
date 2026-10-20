# 武将名册、忠诚与继承：独立高层还原

原 ROM SHA256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

`source/recovered/officer_transfer.py` 是根据机器码手工恢复的独立玩法算法，并非开发者原始源码。16 个有明确边界的服务覆盖城市名册迁移/招入/移除、三个忠诚入口、城首排序、电脑继承决策及写回、玩家继承写回及离队。代码不执行 ROM、不包含汇编 IR/ROM adapter，也不使用空图形函数代替流程。

## 必须更正的旧标签

物理 bank10 的 `A006 → CF3F`、`A009 → CF7C`、`A00C → D00C` 都是**忠诚调整**，只写武将 byte3。`D61E` 的原字节是 `60`（RTS），没有隐含的政治转属操作。`A003 → D717` 是场景控制入口。旧战斗/单挑分析中把 A006 标成“转属”、A00C 标成“政治移除”的描述应以这里的实际字节证据为准。

真正名册写入位于其他银行：bank27 `ACF0` 招入、`AD41` 迁移，bank25 `BDBB` 移除，bank26 `C099` 放逐。它们的作用范围分别列在下表；招入不会自动把同一 ID 从别处名单删除，因此不能当作完整跨势力转移交易。

## 入口与行为

| 高层方法 | 原 ROM 入口/范围 | 已还原的作用及停止边界 |
|---|---|---|
| `loyalty_for_recruitment` | bank10 A006 → bank11 CF3F | `u8(70 + 徳//10 - 原忠诚)` 先回绕，再夹到10..90；只写忠诚 |
| `loyalty_after_leader_change` | A009 → CF7C | 新君主在该君主索引的家属名单内则全体免调整；否则徳的整除差值、回绕/饱和、减10、夹到10..99 |
| `loyalty_after_capture` | A00C → D00C | `max(10, max(0, 51-abs(50-忠诚)))`；只写忠诚 |
| `delete_city_officer` | bank25 BDBB..BE00 | 武将状态低2位 OR3、删选中城槽并压紧名单；空城 owner=`(旧byte0&F8)\|7` |
| `release_city_officer` | bank26 C099..C0E1 | 状态低2位清0、byte5=所在地、名单左移；空城 byte0 整字节写7；0402++、042C=ID；返回待对话D4，止于C0E2 |
| `move_roster_group` | bank27 AD41..ADF1 | 先向目的城追加；若目的城含君主，交换到首槽并写君主byte1；再删除来源首个匹配 ID 并压紧 |
| `recruit_officer` | ACF0..AD36 | 按非FF人数写到第17+count偏移、状态2；旧状态1跳过忠诚调整；止于AD37的UI尾段 |
| `promote_city_chief` | bank11 C9A5..CA18 | 首个忠诚100立即选中；否则用 `u8(忠诚+徳)` 最大值，平手后项优先；交换到城首槽 |
| `repair_ruler_city_chiefs` | C98F..C9A4 | 对30城逐一做上述城首修正 |
| `choose_successor` | CA87/CAAD、CB05 | 家属名单顺序优先；再按徳最大、平手后城后槽；只要存在于该owner的名单，**不检查HP或状态**；返回候选FF表示没有 |
| `recalculate_ai_followers` | CB81..CC11 | 调忠诚；忠诚<31时抽cursor1随机数，<20则清状态、写byte5=城；**不删除该ID**；保留早退出栈帧造成的0045额外递增 |
| `install_ai_successor` | CB52..CB78 | 君主byte0写新ID，新君主忠诚100，处理AI随员；君主byte1不改；6F8B=FC后停，等待外部ack1 |
| `resolve_ai_leader_death` | CA19单君主前缀、CA37/CA68 | 只处理君主controller byte3=3；leader状态2跳过，即使HP=0；其他状态先标3，选择并安装继承人；没有继承人只写leaderID=FF、6F8B=FB后停 |
| `set_city_chief` | bank26 C101..C131 | 找到首个同ID，和偏移17交换 |
| `commit_player_successor` | bank25 BF85 / bank26 C25D | 新君主ID、城首交换、0402++、042C；手动路径才写君主byte1，自动路径额外清04D0；分别停在BFA9/C27D对话入口，返回D3/C2 |
| `recalculate_player_followers` | C289..C341 | 可选忠诚调整；低忠诚且cursor0采样<20时真正左移删除名单并清状态；不写byte5，不清空城owner；结尾新君主忠诚100、0401=return_state、0402=0 |

城市结构只声明经这些路径验证的字段：每城32B，名单偏移17..26；君主记录每条8B，byte0是君主ID，byte1是在上述写入点使用的驻城索引；武将每条12B。大部分政治扫描用城市byte0低3位；招入经过F368，实际掩码为0F，模型仅声明其结果0..6的七条已证实君主记录。controller代码3保留机器意义，不把它误称城主ID。

兵数字节8/9完整保留。本验证专门把记录设为raw16=`ABCD`，没有把高6位清成0或按显示的10位兵数重写。

## 原程序边界与 quirks

- 招入按人数插入，而非寻找第一个空槽。名单有洞时可能覆盖已有项；满10人输入可写到偏移27。正常UI容量门槛属于上层，核心保持这一行为。
- 搬迁核心没有同势力或容量判断。目的扫描、来源查找均无10槽边界，Y会按8位回绕。测试包含同城源/目的别名、重复ID、同址追加溢出写回；未找到值的无限扫描由模型在256位置后显式抛 `UnboundedOriginalScan`，不伪造成功。
- 城首得分加法先按8位回绕。继承选择对HP0、状态3记录也能选中；这是代码行为，不代表已证明的正常玩法许可。
- 家属免调整检查的是**新君主ID**。原 CF7C 早返回还会保留旧 `$22/$23` 指针；玩家调用者 C2F1 随后读取该指针，离队时可能清该指针的状态而删除当前槽ID。独立玩家函数保留此副作用，调用者须提供原来有效的武将记录指针；任意I/O/ROM或RAM控制字段别名不在该高层API的已验证域。
- 电脑随员遇到FF或新君主直接尾跳到CB98，留下返回帧；最终 `$0045=30+早退出帧数`。6496例的实际指令验证包含该控制流后果。
- 电脑低忠诚离队保持名单ID，玩家离队真正删除，二者的 byte5/空城owner写入也不同。没有把这些路径统一成常见游戏规则。
- 没有继承人的路径只清君主ID并等待FB事件。没有发现该有界段把全部城市中立化，不把它称作已完整恢复的“势力消灭”。

## API 与明确的外部等待

```python
from source.recovered.officer_transfer import OfficerTransfer, TransferData

rules = OfficerTransfer(shared_memory_64k, TransferData.from_rom(rom_bytes))
result = rules.move_roster_group(3, 4, [30, 31], ruler_record=0x6F07)
pending = rules.resolve_ai_leader_death(0)
```

可直接对共享64K内存调用。`selected=None` 读取原0481列表；`ruler_record=None` 读取原EE/EF指针。有效常规城市索引0..29、君主索引0..6；放逐槽偏移17..26。`manual_choice`、`process_followers`、`return_state` 必须明确传入，避免省略参数时改变流程。

AI继承等待条件是 `$6F8B == 1`。源码仅写FC/FB并返回待处理事件，既不自动设置1，也不自动处理对话。原CA19收到ack之后调用C98F修正城首，再继续下个君主；结尾D249/BEC7的月轮/内政控制属于外部协调。玩家D3/C2/D4对话、AD37的UI尾段也显式外置。

这里的16个服务是有边界的玩法恢复，尚不包括完整人事/外交菜单控制器、全部城市owner改变链、渲染/NMI/音频、战争结果到城市结算的整条交易。纯语义API不能直接冒充旧IR控制器需要的完整寄存器/mapper hook。三个忠诚方法额外报告直接入口的A值及C/V/N/Z；其他方法不宣称完整CPU寄存器、栈、所有临时指针或mapper效果。

## 原 ROM 验证与复现

`validation.json`：**6,496 个实际原ROM CPU差分案例，0失败**。每例比较全部8192B SRAM；另比较对应0481/0580缓冲、控制字段和RNG游标。忠诚入口比较A及C/V/N/Z，包含原V保留的家属早返回。名单搬迁48例为源/目的同址。另有2项源模型的无限扫描/未验证指针域拒绝检查，独立列出，不计入6496个原ROM案例。验证是CPU执行、静态服务边界和内存结果证据。

上下文来自 `analysis/phase5/runtime/city-info/menu-0-{ram,sram}.bin`，每例明确覆盖城/君主/武将记录，并把E1..E3同步到oracle真实映射的bank pair。没有修改ROM；没有替换原函数；有UI等待的段在原入口PC停止。该轮没有声称在完整核心中自然导航过继承、转属或放逐，也没有新增对应截图实证。

```sh
.venv-trace/bin/python scripts/analyze_officer_transfer.py "/Users/paulasmith/Downloads/三国志2超级版.nes"
.venv-trace/bin/python scripts/verify_officer_transfer.py
```

`evidence.json` 保存19段真实代码字节、SHA256、字段和入口范围、16服务源码行号；`original-ranges.asm` 跳过EE07后两字节inline目标，避免把目标指针误反汇编为指令；`tables.json` 保存原7条家属顺序与256B随机表。所有结果都是逆向恢复/字节证据，不是原始开发源码。

### 恢复出的host计时确认段

上述高层继承服务不自行确认；统一入口的pair25/26调度器另外包含实际host计时段。受控初值0401=11、040C=0的FC路径，第240次调用转sub12，仍FC；第480次由原CBBD..CBBF写6F8B=1。FB从sub12开始，第240次写1。720次连续调用逐次匹配原ROM寄存器、2K RAM、8K SRAM和mapper，未注入ack。单位为控制器调用，不是已验证视频帧；前置C7E0跨银行renderer仍是明确依赖。见[统一入口回执](../source-integration.json)。
