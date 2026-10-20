# G106完整指针与索引生命周期合同

稳定1526个原间址位置，本轮只改变G106七处权威逻辑访问分类：BF74/BFA0/BFA6/BFDF/BFE9/BFEC/BFF2。阶段26为1191不交、81可能、254未知，阶段27为1198不交、81可能、247未知；候选335→328。没有把裸入口或未知中断环境排除，也没有重新扫描其他组来增加本轮数。正式城市辅助字段名称仍未知。

BF0A原0514==0分支在F2AF正常返回后，把当前完整00/01复制到1A/B。模型要求BF1B开始的must-builder仍活跃且BF24当前00完整typed；低半旁路、部分写与join不恢复旧代指针。只有此完整父链的Y域是有限字段：BF74=11，BFA0=2/4/6/8/14，BFA6=3/5/7/9/15，BFDF=2/4/6/8/11/14，BFE9=3/5/7/9/15，BFEC=2/4，BFF2=3/5。rawcity0..255保持6000+32×byte，不把30..255叫合法城市。

BF9E/BFB3保存原Y到真实栈，EBE9/EA7C全原闭包无stack操作、无X改写且写域低于1A；typed1A域的全部rawY store EA是6000..80DF，不会写ZP/内部RAM镜像/栈，因此normal/no-interrupt时1A保持。返回Y为原11则11、否则(rawY+1)&FF；BFEC只读，返回Y=(rawY+1)&FF。裸BFEC的旧通用readonly保存不是新增typed写安全合同。8000..80DF潜在mapper地址只列地址域，执行0条，不声称硬件无副作用。

原CPU独立合同共5891例：完整RTS 5632（2560完整BF0A父caller+3072 typedpointer/rawY helper）、256构造前缀、3裸单指令反例前缀，另16模型检查；Source案例0。裸6001/601C/601F可以直接读辅助字节；typedhelper的rawY也可直接写辅助偏移，不能把完整父链无命中扩成整个函数/ROM未用。Source全RAM差分和10个被动原机callee另计，不重复为静态案例。

logical-vs-dummy-bus-contracts单列表。LDA额外未修正页读取只在crosspage时存在，STA无条件有其dummy读取。这里py65只逻辑内存访问，不产生dummy周期；Native另外实捕11个STA dummy。构造与裸输入是明示CPU夹具，不伪称自然菜单可达，无新增IRQ/NMI、ack、ready。A006/BAB3完整父controller和ECEE依赖未由这些合同闭合。

复现：.venv-trace/bin/python scripts/analyze_unknown_pointer_phase27.py ROM；.venv-trace/bin/python scripts/verify_unknown_pointer_phase27.py ROM。仅写新phase27。
