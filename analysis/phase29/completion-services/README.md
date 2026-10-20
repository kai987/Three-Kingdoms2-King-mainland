# 精确战后阶段3与城市首将收尾

PostbattleCompletionServices(PostbattleParentServices)的NEW5为A006/BAB3/BBA0/BBB8/BC00。stage2正文继承冻结28；0/1仍停在原dispatch目标。stage3每次独立调用读87：非负即正常RTS，不yield等待、不写ack；负才真JSR BBB8，返回后写7A=1/0400=13/0401=0。0500/0501保留，不能把原机后续淡入与城市控制器重新初始化混成此body写入。

新增精确协议81原位置/166B。旧promote_city_leader/finalize_city_ownership及phase6组合已有玩法语义，本轮不称首次恢复owner/chief算法；新增是完整register/scratch/stack/mapper/read-write顺序与父调用。F25F仅选择E1数据页16，F2AF建城ptr，BC00复制00/01到0A/0B后F368借00/01读leader，保持完整原协议；外层EE07恢复代码pair但不回滚8000页副作用。

BBB8仅outcome0写byte0=(old&F0)|(0507>>4)，高nibble保留。然后当前城及9D72+u8(city<<3)邻接逐项修首将，只精确FF终止，Y bytewrap，不额外加8项limit或signsentinel。合法30城表已有FF不扩成任意rawcity的正常资格；raw30..255单独作为机器数据/实际CPU输入对照。

BC00读owner&0F，仅7跳过。0..6是合法ruler，8..15保留F368合法七项表之后的相邻机器字节，不clamp或改&7；这不是十六个合法ruler。owner8→5F20需要显式硬件输入，缺失即真实PC BC1C/原SP的可恢复ServiceWait；提供共同输入后同generator继续，未改冻结Shared。其他ServiceCall仍必须statusreturned+实际PC/SP。

名册17..26十槽找firstequal，不因FF早停，不查HP/status/地点。匹配时即使同槽/同值仍做两次实际store；保存Y到真实栈，firstslot和foundslot每次重读live0A/B。受控FFF9裸指针例使首store写000A将pointer变FFFF，第二store真实落0011；裸city+1和city+11亦可读写辅助偏移，不能将完整F2AF城基址无aux命中泛化到任意BC00。

本体Source 2853例（2827受控、26被动软件输入），{"actual_caller_RTS": 2847, "strict_dependency_prefix": 6}，另9 guards；81位置动态81/81。完整2048RAM含闲置栈、8192SRAM、AXYP-SP-PC、四实际页、交织logicalIO、共同声明N163及逐写EA/value均比较。SourceCPUcallbacks0、IR0，无新NMI/IRQ/ready/ack。原CPU不是dummy总线模拟，Native的STA dummy单列。

新增同generator回归组inherited_stage2_ECEE_protocol_in_completion_driver有2例：new-driver-stage2-ECEE-resume/A006及/BB93。它们均实例化本轮PostbattleCompletionServices，并断言实际使用新的_drive；先与原CPU对齐真实ECEE入口，再验证只返回status=returned但未恢复PC/SP的服务不会推进、不会重复已发生的状态或IO、保留同一个pending ServiceCall与program generator，最后接真实冻结Shared服务恢复完整原caller RTS。两个完整受控父序列各计1个CPU例，不再将内部检查计作独立guard，也不是原机跨帧淡出完成或新增Native输入。

26正式NEW5软件输入与8个Root冻结CC29/完整D4F0入口分开，见../cpu-completion；N163不是现场捕获。自然退却、受控祖先19已知准备/更早未知分别保留。原机同值roster写不是非平凡swap实证；非平凡swap、FF洞、重复firstmatch、rawowner和livealias是受控软件对照，不能冒称自然玩法。

本模块不改城市辅助字段正式名、不改变冻结1526/328账本，不覆盖stage0/1，也不宣称全战后/全ROM完成。复现仅运行新29：analyze_postbattle_completion_services.py ROM --import-native-callees --import-only；verify_postbattle_completion_services.py ROM；analyzer ROM --evidence-only。
