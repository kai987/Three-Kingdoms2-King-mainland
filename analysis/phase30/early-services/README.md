# 阶段30战后前两态与AI安置精确协议

PostbattleEarlyServices继承冻结29Completion，新增A006/BAB3/BAC1/BB3D/BC46精确owner。原四阶段0/1现在真实执行，2/3继承既有正文；BC46三表为BC52/BD59/BD67，非法mode不执行表外字节。Source无CPU/IRfallback，无新ready/request/RNG/PC/栈伪造或自动完成未知服务。

手工具名协议覆盖410原指令位置/912codeB+6B inline表。process_ai_officers与finalization_phase已经有独立玩法语义，本轮不称首次恢复。新增信用是完整caller、register/flags、scratch、原栈、mapper、交织logicalIO协议。旧高层依赖标签BB37/BB8D不等于实际JSR；原BB36→BC46→BB39及BB8C→BC46→BB8F已由bytes和CPU对照核实，历史文件不改。原CPU完整父病例BB36计397、BB8C计147，逐row保留连续PC/实际REG/SP/栈顶4B；这是软件oracle证据，不等于Native到达数。

stage0先写五组CHR cache8/9，F368取0507高nibble；stage1取低nibble。controller整byte恰3才AI，不能&3。human分别按outcome零/非零交接0500=13/14、sub0、050B=17/2；不替人类选择或完成下一态。AI side80/0，mode为stage0 outcome0→0、非零→2，stage1 outcome0→1、非零→0。真实BC46返回后才INC0501，守住samecaller真实栈。

mode0先当前城17起填，mode1只邻城，mode2先源城052A第一FF；满城时原04可保EADE目标高字节BD，不重置为0。收军只排active sidebyteFF，不排active officerIDFF；首将扫描20槽，遇FF继续。临时表填终止符是至少一次的do-while，可超过21。邻城收集9D72+X负值终止/Xbyte递增，不能写固定8for；随后两个消费循环才真CPY8。既有名单/城市资格与裸helper的rawbyte域分列。

BD96每次live00/01读写；raw offset>=27仍先写一笔后比较，caller有效容量不泛化到裸输入。逃走将匹配时真实PHA/PLA先写052C再名册。空邻城分配后整个ownerbyte替换为ruler，不虚构status2/recordlocation同步。overflow首轮比较rulerleader，释放后02被u8(city<<3)覆盖，后续ID可能按rowbyte变status3；其余status低2清0并按E856/真实bank16邻表写byte5。F25F更新E1数据窗，F266更新DE主数据窗，两者原副作用各自保留，不全四页还原。

本体Source 1546例（1506受控，40被动软件输入）：{"actual_caller_RTS": 1540, "strict_dependency_prefix": 6}；另11guards。410位置动态410/410；未命中0不叫全路径证明。对照完整2048RAM含闲置栈、8192SRAM、AXYP-SP-PC、四页、交织logicalIO及共同声明N163。py65不是硬件dummy总线模拟；原机观察独立列示。

新30owner实际动态跑stage2 ECEE缺服务→假returned未改PC/SP不推进/同pending与generator→真实Shared完整恢复；stage3每次新callback非负87真RTS、负才结算，以及缺5F20的真实设备wait/共同输入续跑。它们是独立软件CPU回归，不是新Native帧、跨帧挂起ECEE或借锁29hash代替测试。

继承setup_fields是旧setup调试键，不能将其中side_base等名字当战后字段定义；这里6F91是mode。入口API为run_entry(actualregisters)或真实ServiceCall，不能用默认构造值替caller。

14份新30实际输入和26份冻结29 NEW5回归分列，正式来源见../cpu-early。独立受控初值覆盖overflow RNG低3位八种选择及cursor255回卷、裸早态phase255的INC0501回零；不称合法UI入口或原机准备。祖先自然与19项已知受控/更早unknown分开；本轮无新增准备。瞬时N163未捕获，共同fixture另列。Native未走到的mode2/BB36不能因受控CPU命中而声称实机到达。字段+1与+28..31正式名称仍未知，冻结访问账本不因此改变；不宣称全ROM完成。

复现仅运行新30：analyze_postbattle_early_services.py ROM --import-native-callees --import-only；verify_postbattle_early_services.py ROM；analyze_postbattle_early_services.py ROM --evidence-only。本轮完成后停止，不自动启动31。
