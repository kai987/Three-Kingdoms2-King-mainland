# 城市菜单与NMI2控制器

源码：[city_ui_controller.py](../../../source/recovered/city_ui_controller.py)。原bank27/28共6330个指令位置，直接结构化函数与分支，不在运行时解释控制IR或执行6502。静态closure原字节、表、带16B头的ROM偏移及REA旧archive均保留。

原CPU对照：712例，其中707完整返回、5严格前缀，4个非返回callback guard。比较全2048RAM（包括stack）、8192SRAM、AXYP/SP/PC、有序端口读写和bank。0个无效/不终止的准备输入明确排除。执行到的本地指令位置为2905/6330；不将静态收录或helper CPU执行算成本地路径覆盖。

此矩阵仅证实本地控制正文，外部helper原CPU只存在于validator；[统一GameEngine纯源码整合](../source-integration.json)另计，没有原CPU callback。调用必须提供寄存器和已有caller帧；显式测试seed_return不属于生产coordinator路径，未返回状态或PC/SP不符不能继续。

主状态16项；主要子表：内政23、军事25、物资16、街市24、状态6的18项。原画面已确认main4物资输送／给予，main5街市／武器店。AD41调动名单保留目标追加、君主置首、源城删除与压紧；C81F保留四件装备的原PPU请求，不假定队列已被NMI完成。

复现：`.venv-trace/bin/python scripts/analyze_city_ui_controller.py ROM`，然后`verify_city_ui_source.py ROM --area city`，最后`build_phase13_city_evidence.py ROM`。再生成前须注意旧receipt失效，不能只改hash声明通过。
