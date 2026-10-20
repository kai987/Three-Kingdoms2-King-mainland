# G107部署指针合同

仅四读B272/B278/B290/B296新增完整producer/return合同。稳定分母1526：1191不交、81可能、254未知；候选339→335、unknown258→254。其它第25阶段权威合同及分类原样继承。B1B0/B2AE/B312算法与数据含义已经存在，本轮不声称首次发现，不同时扩展另一条链。

两formation仅有固定F266这个callee，原数据窗最后真实选raw26→physical6，8/9/31代码窗不变。first先raw30→16查byte邻接窗口，匹配时raw31→17查template（negative fallback不走17），offset=32×byte mod256；second邻接/template均在16，offset=34×byte mod256。读取bank6表完整low/high word，以真实carry加offset；原city左移一位索引按byte截断，因此256城市原始字节都保留，表共128word。22..25为单独组游标，20/21被重新构造，不能保存旧profile/city类型。

正常city0..29，两表基址和所有byte索引均为bank6 ROM。完整raw域也保留：first564完整word，second4606完整word，含内部RAM镜像；second保守offset/Y域有2000..200E潜在IO。它们只作地址合同，未给硬件输入不执行该读、不声称无副作用/合法城市。四读logicalEA与6000..63BF城市aux不交仍成立，不意味着raw数据有正常坐标意义。

静态postcondition在完整formation普通二进制无中断返回后建立pointer20；两个真实callsiteB25D/B263构成B1B0至四读的必经cut，后续不写20/21。不从裸B272等中段造指针。三个bare读city+1/+28/+31原CPU反例保留，证明单看同一个读PC不够。第一侧真实Native来源只旁证一条路径，不是所有raw输入均可达的定理。

独立原CPU合同36443（Source0）：1024个完整rawformationcaller RTS、600个完整typed B1B0 RTS、34816个完整low/high构造prefix、3个裸访问反例prefix。prefix不是callee返回；raw IO地址枚举执行0指令且不加入CPUcase。另13个模型guard。完整表/真实原字节与producer/caller写清单可复查，不凭名字或Y独立投影拼接不真实word。

LDA IndY仅跨页才额外读未进位页；dummy公式在无跨页时只是候选，py65本身不发该读。逻辑地址与条件dummy域独立计算，和Native STA的无条件dummy规则分开。本轮没有赋予城市+1/+28..31正式名称，也没有unused/padding结论。
