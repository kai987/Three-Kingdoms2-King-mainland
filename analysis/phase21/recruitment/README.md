# 城市登场与在野录用

[CityRecruitmentServices](../../../source/recovered/city_recruitment_services.py) 独立手写 physical11 `C5B9..C794`，通过具名函数实现城市登场、偏好概率、在野录用、首FF写入与实际双PLA返回。新手工范围是225个原指令位置/476B；`C690..C6CB` 是偏好分支的一部分，包含在此范围。城市指针/资源限制、名册前缀计数、君主定位、忠诚和固定RNG/mapper服务复用冻结的独立源码。生产侧不执行ROM/CPU、不解释IR、不读取程序JSON或运行时生成代码。

`C5B9` 对30城依次先做登场，再做在野录用。`C5D2` 要求owner低3位等于当前君主、原随机门槛小于10、首FF前人数少于10，然后按原城市ID/年表判断。年字节先减100再与原年度比较；不存在额外添加的十项上限或FF终止规则。普通年度的FF/yearFF会被年份门槛挡住；raw年度155及以后可能进入其后机器字节，保留原条件和明确执行预算。

`C6CC` 在owner、原难度概率及名册容量通过后准备8个邻城，进入`C71A`。只对status低2位为0的记录作概率和所在地检查；所在地是本城或邻城时提交。它没有HP检查。君主4的109/112/55/183/144、君主2的86/99/57/165/156、君主3的107/234/235/213/47得到90阈值，其余为10。成功保留status高6位、将低2位置2、写入首FF、重新计算忠诚；不改体力或所在地，不附加金币费用。

成功路径`C792/C793`的两次PLA丢弃C6CC返回层，再RTS到外层。正常`C5B9`父驱动拥有这个真实caller；单独调用C6CC/C71A/C765可能返回`nonlocal_return`，绝不冒充本层RTS。容量由父流程首FF前人数判断；直接绕过这个门槛的裸suffix仍按8位Y扫描，可访问城市tail/下一记录。全256个位置无FF时是原无限循环；源码报告`waiting`并保留栈/循环，不写假FF、ready或ack。

## 237项边界与阶段20勘误

固定`E89A`完整字节为`8E 53 00 AE 54 00 BD BA E8 EE 54 00 AE 53 00 60`。它保存X到0053，使用0054随机游标，最后恢复X再RTS。阶段20只看到内部写X而未完整纳入返回恢复，因而对237项循环界限的保留判断不完整；本轮补充覆盖它，旧阶段20文件保持原字节。

在无新增中断的普通callee合同下，`C66F`和`E89A`均保持X，所以未成功的`C71A`恰扫237个记录：ID0..236、status有效地址63CB..6EDB，结束pointer22为6EDC。四个完整扫描例都验证这一点；status0且所在地不合格的例实际调用E89A 606次，其他status例不调用该内部随机服务。这里不声称已经观察到Native中断覆盖0053，也不将这段扫描误称HP维护。后续首FF扫描是另一个未定界的raw循环。

## 原CPU差分范围

当前2448个独立原CPU父用例：2415个真实caller RTS、30个真实非局部返回、1个原循环等待、2个缺服务严格前缀；另3个源码guard。其中5个从保存的Native actualREG/MAP/N163上下文通过原CPU真实前序产生callee输入，其余数值/帧fixture逐例明示。它们不冒充原Nestopia内部CPU录制。比较完整2048B RAM（含全部栈残余）、8192B SRAM、AXYP/SP/PC、有序IO读写、四个PRG银行及N163 RAM/地址/自增，无闲置栈排除，source CPUcallbacks为0。

新body动态命中225/225个原指令位置；这是位置覆盖，不是所有路径或全部输入证明。HP0/1/99/FF、记录0/109/236、所在地本城/邻城/不合格、偏好全256byte、年份门槛、名册空洞/满额/裸tail别名、无FF循环和缺固定服务分别列明。正式阶段20自然母档没有status0在野将；该原机路线的237次空扫不能作为成功录用实证，原机成功证据由runtime域单列。

```python
rules = CityRecruitmentServices(memory, rom, services=readable_services)
rules.run_entry(0xC5B9, registers=actual_caller_registers)
rules(service_call)  # 原physical10/11与真实caller帧
rules.resume()       # 同一pending服务/循环，无自动确认
```

PUBLIC继承Negotiation既有入口并加C5B9/C5D2/C66F/C6CC；C71A/C765仅定向LOCAL。新组合入口`CityRecruitmentGameEngine`保留旧1..20源码不变，真正A000调用通过具名方法别名进入本轮实现；裸C6CC非局部终点保持terminal，重复同call不再pop。

```sh
.venv-trace/bin/python scripts/verify_city_recruitment_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_recruitment_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[原字节](original.asm) · [静态目录](static-catalog.json) · [差分回执](validation.json) · [证据](evidence.json) · [有效地址CPU轨迹](../cpu/runtime-trace.json)
