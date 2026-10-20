# 数据表与算法的证据报告

本文来自对用户提供的 ROM 字节、实际 6502 指令执行及提取字形的分析。它不是原始源码，也不是完整游戏复刻。所有偏移均从 `.nes` 文件第一个字节开始计数，包含 16 字节 iNES 头。`$xxxx` 为 CPU 地址；可切换窗口的地址必须同时指定 PRG bank。

ROM SHA256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。

## 已确认的结构

| 发现 | ROM 偏移 / CPU 地址 | 原始字节示例 | 置信度与限制 |
|---|---|---|---|
| PRG 256 KiB、CHR 256 KiB、mapper19、battery 标志 | `0x000000` | `4E 45 53 1A 10 20 32 10 00 00 00 00 00 00 00 00` | 高；iNES header，不是实际 PCB 鉴定 |
| NMI / RESET / IRQ vectors | `0x04000A` / `$FFFA` | `00 F8 00 E0 2D FB` | 高；入口分别 `$F800/$E000/$FB2D` |
| 30 条 × 32 字节初始记录 | `0x020C10..0x020FCF`，bank16 `$8C00..$8FBF` | 首条前 12 字节 `07 00 0F 27 0F 27 0F 27 0F 27 63 64` | 高：大小、位置、RAM 地址；中：城池/区域语义 |
| 237 条 × 12 字节武将记录 | `0x022010..0x022B2B`，bank17 `$8000..$8B1B` | ID0 `47 40 18 44 34 00 D0 07 00 00 51 25` | 高：表及武将身份，已与姓名字形联接；属性名称仍待验证 |
| 初始化额外复制 3 槽相邻数据 | `0x022B2C..0x022B4F`，bank17 `$8B1C..$8B3F` | `4A BE 0B D0 24 D1 49 D2 FF FF FF FF` | 高；不能把这三槽算成武将 |
| 237 条 × 13 字节姓名字形记录 | `0x022DC4..0x0239CC`，bank17 `$8DB4..$99BC` | ID0 `6A 2A 2B 3A 3B 2C 2D 3C 3D 2E 2F 3E 3F` | 高：字形地址及布局，提取图确认为“阿会喃” |
| 256 字节随机排列 | `0x03E8CA..0x03E9C9` / `$E8BA..$E9B9` | 开头 `3E 4E 4F 83 0E C9 7F 5D` | 高；0..255 每个值正好出现一次 |

`city_records_raw.csv`、`general_records_raw.csv` 保留全部原始字节，并列出数值解释用的 LE16 / 位字段。字段采用 `byte_00` 等中立名称。`recovered_tables.json` 保存逐条 CPU/RAM/ROM 地址、原始字节、姓名 CHR 寻址信息及置信度。名字图在 `../assets/names/index.html`，可以按 `id` 联接。

姓名图已直接观察的对应关系：ID0 阿会喃，ID2 伊籍，ID38 関羽，ID47 甘寧，ID55 姜維。游戏字体包含日文字形，不能仅由文件名推断所有文字为简体中文。其余姓名尚未逐一转写为 Unicode。

## 两表的初始化复制与有效数量

bank30 `$DD8B`（ROM `0x03DD9B`）先保留 `$6F43`，清零 `$6000..$6FFF`，再恢复该字节。该函数后段 `$DDCD..$DE55`（ROM `0x03DDDD..0x03DE65`）执行：

```text
select_8000_bank(0x30)       # 在本 ROM 的 32 个物理 bank 中别名为 16
copy(cpu=0x8C00, ram=0x6000, length=0x3C0)
select_8000_bank(0x31)       # 别名为 17
copy(cpu=0x8000, ram=0x63C0, length=0xB40)
```

第一段循环结束条件原始字节位于 `0x03DE17`：`AD 04 00 C9 03 90 DF E0 C0 90 DB`，对应累计 `3*256+192 = 960` 字节。第二段位于 `0x03DE5C`：`AD 04 00 C9 0B 90 DF E0 40 90 DB`，对应 `11*256+64 = 2880` 字节。

记录寻址由固定 bank 的函数确认：

```text
CPU $F2AF，ROM 0x03F2BF：RAM pointer = 0x6000 + uint8(A) * 32
CPU $F2D7，ROM 0x03F2E7：RAM pointer = 0x63C0 + uint8(A) * 12
CPU $F387，ROM 0x03F397：bank17 ROM pointer = 0x8000 + uint8(A) * 12
```

第二段虽复制 240 个 12 字节槽，正常武将循环以 `0xED = 237` 为界。例：bank25 `$A27B..$A293`（ROM `0x03228B..0x0322A4`）调用 `$F2D7`，然后 `INC $0010; LDA $0010; CMP #$ED; BCC ...`；另一处 bank25 `$BA11..$BA24`（ROM `0x033A21..0x033A35`）使用同一上限。第 237 槽起字节已呈 `$BE4A/$D00B/$D124/$D249` 等指针，作为额外复制槽单独输出。

第一表 30 条记录的 `+2/+4/+6/+8/+12/+14` 共六组 LE16 均为 `0x270F = 9999`；`+10/+16` 均为 99；`+11` 均为 100。它说明这份 ROM 的初始数值被统一设为高值，但没有原版 ROM 对照，不能据此精确宣称哪些字节是修改补丁。`+17..+26` 使用 `FF` 为空，其他值都落在 0..236，可作为武将 ID 列表继续联接；其城市含义需要动态界面确认。

武将表前五个字节均为 8..100 范围的单字节属性；第六字节初始全零；`+6/+7` 与 `+8/+9` 为后续代码以低高字节读写的数值；`+11` 被代码拆为低 2 位、中 2 位、高 4 位。样本关羽（ID38）原始字节 `61 61 54 63 58 00 E8 03 BC 02 2C 1A`，前五值为 `97,97,84,99,88`，两组 LE16 为 `1000,700`。体力、武力、智力、忠诚、魅力等为待验证的字段候选，未作为确定字段标题使用。

## 姓名不是普通字符编码

bank26 `$D2EA..$D342`（ROM `0x0352FA..0x035352`）取得 `$0664,Y` 的 ID，通过移位和加法计算 `13 * id + $8DB4`。`$D34A`（ROM `0x03535A`）的 `B1 00 8D C1 00` 把首字节存入 `$00C1`。IRQ 的 `$FBF1`（ROM `0x03FC01`）执行 `A5 C1 8D 00 98`，将其写入 mapper `$9800`，选择 PPU `$0C00..$0FFF` 的 1 KiB CHR 页。

随后每个 tile 编号加 `$C0` 写入 OAM；这仅把页内 tile 映射到 PPU `$0C00`，提取时不应再向 CHR ROM 文件地址加 `$C0*16`：

```text
chr_file_offset = 0x40010 + chr_bank * 1024 + tile_in_page * 16
```

每条记录的剩余 12 字节最多表示三个 16×16 字符，四个 tile 按左上、右上、左下、右下排列。`FF` 为剩余空间的终止/填充。布局表在 bank26 `$D38B`（ROM `0x03539B`）：

```text
A0 30  A8 30  A0 38  A8 38
B0 30  B8 30  B0 38  B8 38
C0 30  C8 30  C0 38  C8 38
```

## 启动、NMI、IRQ、银行控制

RESET `$E000`（ROM `0x03E010`）始于 `78 D8 A9 00 8D 00 20 8D 01 20`：关中断、清 decimal flag、禁用 PPU NMI/显示；通过 `$2002` 等待垂直空白，初始化 APU、堆栈并清零 RAM `$0004..$07FF`。初始化将 `$007A=0`，进入 `$E066` 的主状态分发。状态0 `$E09A` 初始化显示/声音后设置 `$007A=9`。

状态分发 `0x03E076` / `$E066` 的原始字节：

```text
AD 7A 00 29 1F 0A A8
B9 7C E0 8D 4E 00
B9 7D E0 8D 4F 00
6C 4E 00
```

即 `JMP(*(uint16*)($E07C + 2*($007A & 0x1F)))`。指针区共有 15 条，后面立即是代码；不能把 mask 0x1F 当成存在 32 个有效状态。目标依次为 `$E09A,$E0DA,$E17D,$E18B,$E221,$E22F,$E2E2,$E2E8,$E36A,$E37C,$E3EB,$E3EE,$E3EB,$E46A,$E3EB`。

银行 helper `$F237`（ROM `0x03F247`）把 Y 存入 `$E2`、Y+1 存入 `$E3`，写 `$F000=Y+1` 及 `$E800=Y|C0`；helper `$F25F`（ROM `0x03F26F`）为 `8C E1 00 8C 00 E0 60`，即保存 Y 并写 `$E000`。NMI 将保存的三组银行恢复后通过 `$4014=02` 提交 `$0200..$02FF` 的 OAM。

`$EE07`（ROM `0x03EE17`）是跨银行调用 helper，而不是普通无参数子程序。调用端 `LDY #bank; JSR $EE07; .word target` 的 JSR 后两字节是内联地址。它保存当前银行，弹出栈上的 JSR 返回地址，以其下一字节为起点读 target，调用 `$F237` 切换银行，构造返回栈并 `JMP ($005B)`。被调函数 RTS 先回 `$EE4D`（ROM `0x03EE5D`）恢复银行，再 RTS 跳过内联地址回调用端。例：bank12 `$A00C`（ROM `0x01801C`）的 `A0 28 20 07 EE 12 A0` 目标为物理 bank8 `$A012`，ROM `0x010022`。`far-call-candidates.json` 列出代码候选银行中可按此格式匹配的全部调用点；它只做字节模式匹配，不能代替控制流可达性证明。

`$EADE`（ROM `0x03EAEE`）则是分支表分发器：输入 A 作为索引，弹出 JSR 返回地址，读取紧接 JSR 后内联 word 表的第 A 项并间接跳转。直接线性反汇编会把这两类内联地址误当指令，所以 Ghidra 的初步控制流/函数数量需要人工修正。

`call-protocol-validation.json` 另有 15 个用实际 ROM helper 与人工 RAM caller/target 构造的执行验证：`$EE07` 包含 JSR 内联地址跨页的 6 例，`$EADE` 包含低索引、索引 wrap 的 9 例。`$EE07` 会改写 A/Y，仅按保存的 `$E2` 恢复连续银行对；不能称它为任意银行布局和寄存器全部保存。`$EADE` 的 A=127/255 边界使 Y 在读取 pointer 高字节前由 FF wrap 到 0，高字节来自原 JSR 末尾 operand 地址，因此这两个索引不能视为正常的最后一个表项。验证常见小索引会跳到目标，目标 RTS 返回外层调用者。

IRQ `$FB2D` 保存 A/X/Y，检查 mapper `$5800 & 7F == 7F`，再按 `$0060` 分派 IRQ 操作。它经 `$8000..$B800` 修改 CHR 页面并重设 `$5000/$5800` IRQ 计数。此为带 IRQ 的画面/字形银行切换代码证据，不能在一个没有 mapper19 IRQ 的平面内存模拟器中验证整段显示行为。

mapper 地址解释参考开发者原始技术社区 [NESdev Namco163 文档](https://www.nesdev.org/wiki/Namco_163)。`$E000/$E800/$F000` 依次选择 CPU `$8000/$A000/$C000` 的 8 KiB PRG 窗口，固定末页为 `$E000..$FFFF`。同名旧游戏存在 [N163 bootleg 硬件逆向记录](https://forums.nesdev.org/viewtopic.php?t=17469)，它只能作为变体背景，不能用于认定本 ROM 与那份 dump 相同。

## 已用实际 ROM 指令验证的算法

复原实现位于 `../../source/recovered/game_algorithms.py`，执行记录在 `algorithm-validation.json`。`scripts/verify_recovered_algorithms.py` 使用 py65 1.2.0 直接执行本 ROM 的函数字节，再与 Python 实现的输出比较。

| 函数 | CPU / ROM | 恢复行为 | 验证样本数 |
|---|---|---|---:|
| 第一表 RAM 寻址 | `$F2AF` / `0x03F2BF` | `$6000 + 32*A` | 256 |
| 武将 RAM 寻址 | `$F2D7` / `0x03F2E7` | `$63C0 + 12*A` | 256 |
| 武将初始表寻址 | `$F387` / `0x03F397` | bank17 `$8000 + 12*A` | 256 |
| 无符号 16/16 除法 | `$EA7C` / `0x03EA8C` | 商与余数，16轮 restoring division | 258 |
| 无符号 24/16 除法 | `$EAA5` / `0x03EAB5` | 商与余数，24轮 restoring division | 258 |
| 6 位 packed BCD | `$E9BA` / `0x03E9CA` | 丢弃百万位，每字节存2位十进制 | 111 |
| 随机排列取字节 | `$E87A` / `0x03E88A` | `table[cursor]`，u8 cursor++，保存 X | 256 |
| 有界随机数 | `$E862` / `0x03E872` | rejection sampling `[0,bound)` | 2048 |

共 3699 个实际 ROM 测试，均通过。另将静态 listing decoder 的全部 151 个官方 opcode 的名称与长度对照 py65 disassembler，全部通过。除法测试包含 divisor=0 的 ROM 行为：商为全 1，余数为原 dividend；复原函数保留该行为。

RNG 使用 4 个独立 u8 游标 `$50/$52/$54/$55`。NMI `$F8A1`（ROM `0x03F8B1`）有 `E6 50 E6 52 E6 54 E6 55`，每次有效 NMI 都推进四个游标。`$E862` 对 bound<15 使用 low-nibble，较大 bound 使用全部字节后拒绝越界。bound=0 会在 ROM 中无限循环，Python 分析 API 明确拒绝该输入。

验证范围仅为 CPU 算术/寻址/随机函数，不包括 PPU、APU、完整 mapper 副作用、IRQ 时间、游戏流程和 SRAM 持久化。它证明这些复原函数与实际机器码的输出一致，不证明一个完整模拟器或游戏复刻已完成。

## 复现

```sh
python3 scripts/inspect_game_data.py '/Users/paulasmith/Downloads/三国志2超级版.nes' \
  --extract-tables analysis/game_data

python3 -m pip install --target /tmp/nes-reverse-py65 py65==1.2.0
python3 scripts/verify_recovered_algorithms.py '/Users/paulasmith/Downloads/三国志2超级版.nes' \
  --py65-path /tmp/nes-reverse-py65
```

所有脚本只读原 ROM。汇编 listing 文件是线性解码的证据，数据区也可能被显示成指令；不能据此把所有字节都视为代码。完整姓名图、银行、CHR、pointer 原字节与 JSON 可以继续用于动态模拟器断点和逐字段确认。
