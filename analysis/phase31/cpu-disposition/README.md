# 阶段31被动软件调用输入

只读复制正式runtime/*/observer中的实际寄存器/PC/SP、原栈、2K RAM、8K SRAM与实际四PRG。每条路线按entry/state/phase/queue-ready/new-A组合只取首现场，不从return−3反推call。被动边界若不能连续证明immediate transfer，则明确unknown/null；同一原有frame直接用于Source，不新push或seed return。

N163未在现场捕获。input-n163.bin、address127/autoincrement及2002/4015/5800/controller输入是共同明确的软件比较夹具；不是原机瞬时设备值。独立CPU/Source回调比较不注入新NMI/IRQ，不等于逐帧或整段不被中断的原机执行。原机连续路线及新核与固定核逐帧五buffer旁证由Root的runtime回执单列，不能推广成所有路径等价。

自然/受控祖先、已知准备及更早unknown原样保留在context。prepared_numeric_bytes和additional_CPU_prepared_numeric_bytes为空只说明本次导出/软件比较没有新增数值准备，不能抹去祖先记录。旧30现场用于回归另列，不复制到此新31目录。本轮不执行旧producer/core，不改旧目录。
