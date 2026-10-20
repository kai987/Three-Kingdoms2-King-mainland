# 城市辅助字节与 AI 补兵源码

新模块 [CityAuxiliaryServices](../../../source/recovered/city_auxiliary_services.py) 直接实现 physical10 `B49C` 的随机入口、两轮名册分配编排，以及 `BD7A..BEC6` 的全部城市选择、补兵、资源购买与预算退出。生产源码不解释 IR、不执行原 ROM，也不使用 CPU fallback。固定 RNG、城市指针、邻城/名册移动、资源支付和 `BEC7` 后续发展复用历史冻结的独立源码；`B5FC` 次级分支是从冻结源码提取的静态 Python 函数，运行时没有读取或编译该文件。

## 实际读法与作用

`10:BD8D` 真实调用 `11:D105`，令 `$20/$21 = $6000+32*城市ID`；这里没有偏移一字节的城市基址。D105 会先限制真正 gold/grain 到9999。`BD97` 读 city+1，`BD9D` 读 city+2，再以连续 SBC 判断二者组成的无符号 little-endian word 是否至少300。city+2 本身是真正金币的低字节。因此 `+1` 保留 opaque/raw 名称；本证据不足以命名为官职、专用收入或其他正式游戏字段，也没有“支付300金币”的行为。

通过门槛后，扫描全部30城中 owner低3位等于当前君主的城市，以及每城全部十个名册槽17..26。`FF` 只跳过当前槽，不结束扫描。低十位兵数正好1000才跳过；首槽候选固定评分100，其余读武力byte1。原 CMP/BCS 在平分时替换，所以靠后的武将或城市胜出。它不额外检查 HP、status、驻城byte5；这里只声明机器条件。

选中后，缺额为 `(1000−troops_low10)&65535`。库存大于缺额时直接扣库存，补兵本身不扣金币；库存等于或少于缺额会进入购买。每次加100库存块、将8bit费用加20，然后减100缺口，直到借位。缺口0也会购买一块；缺口恰好100的整数倍会多买一块。费用保留8bit回绕，`D36F` 支付失败的 carry 被调用者忽略，仍继续增加库存并写兵。最终将武将完整兵word写成 `03E8`，会清除原来的高六位。库存加减保留16bit运算，不擅自改成9999上限。

最后才扣 AI 预算2。预算减至0或借位时，原 `D152` 丢弃自己那层返回地址并从上一层真实 caller 返回；源码保持这个栈协议。预算足够时重新从全城选择开始，再无候选则直接 tail 到原发展流程。

## 验证与边界

当前回执 192 次原CPU对照：191 个完整实际 caller RTS、1 个缺少 E8AA 服务的真实前缀；另有 9 个源码 guard。比较全部2048B RAM（含闲置栈残余）、全部8192B SRAM、AXYP/SP/PC、有序端口读写、全部PRG银行与N163 register image。生产与 source侧 CPUcallbacks 都为0。准备的数值/名册边界单列，包括空名册/首FF/中间空洞、平分/跨城/重复ID alias、兵高六位/低十位1001..1023、库存等于缺额、不足支付、预算0/1/2/3/255、栈wrap。raw边界不当作合法自然玩法。

739 个新控制body位置已静态锁定原字节，其中 267 个被本矩阵实际执行，472 个未动态覆盖。原始字节全集并不证明全部运行路径都测试过。B5FC外交/请求分支的 `F8` 等待保留原 busy loop 和明确源码预算，未把未知请求当已完成；本矩阵完整返回只覆盖回执列出的输入。

两个高价值 B49C 输入从冻结原核心 frame34623 的 RAM/SRAM 开始，在明确的 E066 AXYP/SP 上用原CPU执行真正 main2 前序，捕获实际存在的 caller 栈；它们不是 Nestopia 内部 PC/寄存器 trace。共同只准备城4真金币257、首将167兵900，保留自然库存9499，城市+1对比0/44。正式原核心双跑由 runtime 域单列，不能把本地 CPU 返回数量当 Native 帧。

API:

```python
rules = CityAuxiliaryServices(memory, rom, services=readable_services)
rules.run_entry(0xB49C, registers=actual_caller_registers)
rules.run_entry(0xBD7A, registers=actual_caller_registers)
rules(service_call)  # 精确physical10/11与PUBLIC入口，同一pending owner需resume
```

PUBLIC 是 A000、A00F、B49C、BD7A。A000/A00F 真实调用将虚调用转到本轮 B49C；旧 GameEngine/coordinator 文件保持冻结，新加组合入口由 Root 单列。源码不会构造 sentinel caller 或自动确认其他 UI/硬件请求。

```sh
.venv-trace/bin/python scripts/verify_city_auxiliary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_auxiliary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[原字节汇编](original.asm) · [静态目录](static-catalog.json) · [验证](validation.json) · [证据与hash](evidence.json) · [实际原CPU caller](actual-caller-inputs/aux44.json) · [有限访问追踪](../cpu/README.md)
