# 城市、君主资料与菜单动作服务

源码：[city_panel_services.py](../../../source/recovered/city_panel_services.py)。原bank25/26共3841个指令位置，直接结构化函数与分支，不在运行时解释控制IR或执行6502。静态closure原字节、表、带16B头的ROM偏移及REA旧archive均保留。

原CPU对照：533例，其中530完整返回、3严格前缀，4个非返回callback guard。比较全2048RAM（包括stack）、8192SRAM、AXYP/SP/PC、有序端口读写和bank。49个无效/不终止的准备输入明确排除。执行到的本地指令位置为2402/3841；不将静态收录或helper CPU执行算成本地路径覆盖。

此矩阵仅证实本地控制正文，外部helper原CPU只存在于validator；[统一GameEngine纯源码整合](../source-integration.json)另计，没有原CPU callback。调用必须提供寄存器和已有caller帧；显式测试seed_return不属于生产coordinator路径，未返回状态或PC/SP不符不能继续。

A02A→BBDE年历标题；A021→AFE5由独立武将资料控制器拥有，A012→B2D7由phase12资料服务拥有，避免混淆。B7D9包含出征初始化与持久数据变更；B859名单删除与B879压紧、A1EB归城查找、A209君主记录非零nibble递减及A240非君主可用武将计数均保留实际算术。E000重启与异步硬件等待保留显式边界。

复现：`.venv-trace/bin/python scripts/analyze_city_panel_services.py ROM`，然后`verify_city_ui_source.py ROM --area panels`，最后`build_phase13_city_evidence.py ROM`。再生成前须注意旧receipt失效，不能只改hash声明通过。
