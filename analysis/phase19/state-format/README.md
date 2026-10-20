# 原Nestopia保存上下文与N163边界

固定原核135dfa6，原ROM与dylib不变。源码原始分块材料及GPL见[upstream](upstream/)。

- CPU/REG7：PC低、PC高、SP、A、X、Y、P。
- CPU/RAM与IMG/MPR/WRM压缩标签0为原文、1为zlib；声明长度严格限制父子范围。
- IMG/MPR/PRG/BNK：4页，每页source index与小端16位物理页。使用实际映射，不能假设DE..E0影子总同步。
- IMG/MPR/N63/SND：REG保存7位地址与自增位，RAM128字节；IRQ3字节仅记录，不伪装时钟。
- NST声明stream结束后保留全部tracked-input footer及零padding，原档不截断、不正规化。

318个存档全部完整RAM／SRAM转储一致；21组原dylib load→serialize寄存器／RAM／SRAM／实际PRG／N163一致，原视频帧0。13个实际映射与影子不同的点全部在往返清单中。每次独立load_game重置原核缓存的serialize_size；不同power-on窗口长度不可混用先前缓存大小。每行保存唯一输出路径和输入／输出SHA。

新增CapturedServiceMemory仅修正旧历史服务bus的N163 127饱和问题。原核NstBoardNamcot163.cpp使端口地址`(address+increase)&127`。新模型1025次全128地址×自增×read/write×canonical/alias及显式read override检查通过。保存状态恢复不运行6502，硬件读值／时序／中断仍需调用者明确提供。

这些是**原核保存寄存器快照与原源边界合同**，不是逐指令Native trace，也不是完整硬件时序重建。[完整验证](validation.json)。
