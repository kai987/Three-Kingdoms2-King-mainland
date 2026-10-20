# 精确文本与nametable请求协议

这是对既有语义TextServices的独立精确caller实现；旧phase10源码保留。运行时具名Python函数解析32种游戏文本数据命令，不解释6502或控制IR。A000/A003/A006、其真实body及EE72 palette cadence尾调用保留AXYP、scratch、现有caller栈、mapper与端口次序。

消费/生产就绪分支的原early RTS返回具体flags和X；不是任务已经清空。命令80/81/86等使用原非局部调用栈终止/换行，消息队列仍由原数据逻辑推进。缺2002输入停在真实LDA地址，续同一owner，不重复先前端口。

所有声明RAM0..13F与200..7FF、8KiBSRAM、AXYPSPPC、银行/有序ports均逐例比较；自由栈残余在此模块明确排除，真实caller返回值/地址与SP必须相同。数学与mapper服务都是独立SceneShared源码，source侧原CPUcallbacks为0。

[源码](../../../source/recovered/text_scene_services.py) · [原CPU回执](validation.json) · [原字节/32表/来源](evidence.json)

源用于SceneCoordinator远端UI调用，不制造一个video frame、按键、IRQ/NMI时间或PCM。所有237姓名数据、音符/浊点、数字、真实队列快照和ready/PPU分支矩阵有准确验证计数；非法文本命令拒绝不是推断该原非法路径正常返回。
