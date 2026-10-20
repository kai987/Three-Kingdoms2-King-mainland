# 阶段25：出仕表指针与非零库存提交

两条零新增准备的自然按键续程分别建原核心与新观察核心对照，每核心各fresh进程双跑。导入祖先存档而非本轮冷启动。没有改status、名册、金币、兵数、RNG、request/ready、PC或栈；原ROM与所有旧核心/旧阶段产物保持不变。

[证据](evidence.json) · [回执](validation.json) · [来源/构建](core-provenance/build.json) · [独立补丁](core-provenance/observer.patch) · [脚本](../../../scripts/capture_native_appearance_pointer.py)

## G033 出仕表链

母档是阶段22原控制流14569，只有原无键输入22帧。ID152真实状态1→2发生在local4，原AI请求在local22回FF。新观察即时证实city3，D471乘积60后建22/23=8B58，C61F从实际8000页bank17读ID152，C624读对应年份；C659写该武将status byte26，随后原city3名单追加。该状态1→2是出仕链，不混称上一轮status0→2在野录用。六次真实表数据读、一处状态写、一处名册写保留在[opcode观察](natural-appearance-pointer/opcode-observations.json)。local4帧末22/23已复用为下一城4的8B6C，不能把这个帧末值倒推为ID152读取时地址。

## 已知库存提交对照

从阶段24原核frame076导入，祖先已经用普通Right将ID30兵800分至900，工作库存9899而城市库存尚9999。本轮仅Down至结束、A，再无键，84帧回原city0/1。local23原B441 JSR F2AF建立city11指针6160；真正B449/B44F两次STA把city+12/+13写为AB/26，真实库存9999→9899，兵数保持900。两次STA前的读是IndY dummy bus周期。它们是已知库存写回，不是未知city+1/tail写者。见[opcode观察](natural-nonzero-reserve-submit/opcode-observations.json)。

## 观察和可复核边界

新核心从官方135dfa6及阶段24已校正、可重建相同二进制的补丁起，另建新目录/新身份。外部静态数组记录40个u32字段，完整ZP00..2F、乘积2A/B、实际AXYP/SP/PC、4PRG页与year/ruler/phase/request；CPU对象布局和原总线调用没有改变。Make显式声明.inc/.hpp依赖，首次构建在新净树进行。源码/原文件/完整补丁/构建日志和不同coreSHA保留。

C5D2、D471和B431真实入口稀疏const复制2K RAM/8K WRAM，序号关联snapshot-index与原始snapshots.bin；没有map.Peek或额外仿真读取。没有瞬时N163/PPU/APU副本，后续独立CPU若需设备环境必须另声明fixture。只有新观察核心有内部事件，不追认固定原核心拥有内部trace。

每新帧保留原256×240PNG、RAM/SRAM及完整未归一化serialized API buffer，原48kHz立体声PCM/WAV完整保存。包括首次serialize API查询与导入时序，全部五域逐帧匹配，所有非空文件双跑exact；raw ABI逐条公开decode_event复核，溢出即失败。本短路线city辅助字节总线事件0，不证明unused，也不赋予正式字段名。Source/原CPU、静态合同、Native观察须独立统计。
