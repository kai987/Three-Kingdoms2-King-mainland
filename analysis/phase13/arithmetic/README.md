# 城市UI的EC22乘法

24bit×16bit得到40bit结果，保留原destructive shifts、scratch和flags；只消费已有真实caller。512项原CPU完整返回，全2048RAM（含stack）、8192SRAM、AXYP/SP/PC、端口与bank，另1项未知入口guard。源码不执行CPU/IR。原字节偏移包括16B头。
