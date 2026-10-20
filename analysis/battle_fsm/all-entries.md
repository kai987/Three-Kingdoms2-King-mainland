# 战场主/子状态逐项索引

16 个主状态、101 个合法主/子组合：其中 98 个来自 pair12/13 本地表展开；状态15另有3个共享入口的外部子阶段。
每项列出条件分支、状态写入地址、调用依赖和完整原始证据。条件保留6502旗标测试，避免将未知辅助函数的返回值臆译成玩法。

## 0: 单位选择与行动菜单

### 0/0 — bank12 $A05E / file $01806E

控制条件：$A066 BNE→$A07A (否则$A068), $A06B BEQ→$A086 (否则$A06D), $A06D BMI→$A086 (否则$A06F), $A07D BCC→$A08C (否则$A07F), $A082 BEQ→$A086 (否则$A084), $A084 BPL→$A089 (否则$A086), $BDC3 BPL→$BDCA (否则$BDC5), $BDE5 BEQ→$BE33 (否则$BDE7), $BE14 BEQ→$BE21 (否则$BE16), $BE5F BEQ→$BE67 (否则$BE61)。

控制状态作用：$A071 STA $0500, $A076 STA $0501, $A089 INC $0501, $BE18 STA $0500, $BE1D STA $0501, $BE70 STA $0501, $BE75 STA $0500。

完整流程：[原始指令与调用链](handlers/state-00-sub-00.asm)；可执行逻辑在 program.json。

### 0/1 — bank12 $A08D / file $01809D

控制条件：$A093 BNE→$A0BA (否则$A095), $A098 BNE→$A0BA (否则$A09A), $A0A8 BPL→$A0AE (否则$A0AA)。

控制状态作用：$A09A INC $0501。

完整流程：[原始指令与调用链](handlers/state-00-sub-01.asm)；可执行逻辑在 program.json。

### 0/2 — bank12 $A0BB / file $0180CB

控制条件：$A0C4 BCS→$A0C7 (否则$A0C6), $A0CE BEQ→$A0FB (否则$A0D0), $A0D4 BMI→$A0FB (否则$A0D6), $A0DB BEQ→$A0FB (否则$A0DD), $A0FF BEQ→$A117 (否则$A101), $A105 BMI→$A117 (否则$A107)。

控制状态作用：$A0E3 INC $0501, $A10F STA $0500, $A114 STA $0501。

完整流程：[原始指令与调用链](handlers/state-00-sub-02.asm)；可执行逻辑在 program.json。

### 0/3 — bank12 $A118 / file $018128

控制条件：$A14A BCC→$A117 (否则$A14C), $A150 BEQ→$A15A (否则$A152), $A15E BEQ→$A192 (否则$A160), $A162 BNE→$A174 (否则$A164), $A16A BEQ→$A174 (否则$A16C), $A176 BNE→$A17F (否则$A178), $A17D BCC→$A192 (否则$A17F)。

控制状态作用：$A154 STA $0501, $A16C INC $0501, $A182 STA $0500, $A188 STA $0501。

完整流程：[原始指令与调用链](handlers/state-00-sub-03.asm)；可执行逻辑在 program.json。

### 0/4 — bank12 $A1B8 / file $0181C8

控制条件：$A1C6 BCC→$A1DD (否则$A1C8), $A1CF BEQ→$A1DD (否则$A1D1)。

控制状态作用：$A1D3 STA $0501。

完整流程：[原始指令与调用链](handlers/state-00-sub-04.asm)；可执行逻辑在 program.json。

## 1: 单位信息

### 1/0 — bank12 $A227 / file $018237

控制条件：无本地条件分支。

控制状态作用：$A227 INC $0501。

完整流程：[原始指令与调用链](handlers/state-01-sub-00.asm)；可执行逻辑在 program.json。

### 1/1 — bank12 $A244 / file $018254

控制条件：$A26A BCC→$A27A (否则$A26C), $A270 BEQ→$A27A (否则$A272)。

控制状态作用：$A272 INC $0501。

完整流程：[原始指令与调用链](handlers/state-01-sub-01.asm)；可执行逻辑在 program.json。

### 1/2 — bank12 $A27B / file $01828B

控制条件：$A281 BCC→$A292 (否则$A283)。

控制状态作用：$A289 STA $0500, $A28C STA $0501。

完整流程：[原始指令与调用链](handlers/state-01-sub-02.asm)；可执行逻辑在 program.json。

## 2: 普通攻击目标选择

### 2/0 — bank12 $A2A7 / file $0182B7

控制条件：无本地条件分支。

控制状态作用：$A2AC INC $0501。

完整流程：[原始指令与调用链](handlers/state-02-sub-00.asm)；可执行逻辑在 program.json。

### 2/1 — bank12 $A2BB / file $0182CB

控制条件：$A2CD BCC→$A30B (否则$A2CF), $A2D3 BEQ→$A2E2 (否则$A2D5), $A2E6 BEQ→$A30B (否则$A2E8), $A2EC BMI→$A30B (否则$A2EE), $A2F3 BNE→$A30B (否则$A2F5), $A2FC BMI→$A30B (否则$A2FE)。

控制状态作用：$A2D7 STA $0501, $A2DC STA $0500, $A2FE INC $0501。

完整流程：[原始指令与调用链](handlers/state-02-sub-01.asm)；可执行逻辑在 program.json。

### 2/2 — bank12 $A30C / file $01831C

控制条件：$A313 BEQ→$A324 (否则$A315)。

控制状态作用：$A318 INC $0501。

完整流程：[原始指令与调用链](handlers/state-02-sub-02.asm)；可执行逻辑在 program.json。

### 2/3 — bank12 $A325 / file $018335

控制条件：$A328 BPL→$A367 (否则$A32A)。

控制状态作用：$A32C STA $007A。

完整流程：[原始指令与调用链](handlers/state-02-sub-03.asm)；可执行逻辑在 program.json。

## 3: 普通攻击确认

### 3/0 — bank12 $A2A7 / file $0182B7

控制条件：无本地条件分支。

控制状态作用：$A2AC INC $0501。

完整流程：[原始指令与调用链](handlers/state-03-sub-00.asm)；可执行逻辑在 program.json。

### 3/1 — bank12 $A2BB / file $0182CB

控制条件：$A2CD BCC→$A30B (否则$A2CF), $A2D3 BEQ→$A2E2 (否则$A2D5), $A2E6 BEQ→$A30B (否则$A2E8), $A2EC BMI→$A30B (否则$A2EE), $A2F3 BNE→$A30B (否则$A2F5), $A2FC BMI→$A30B (否则$A2FE)。

控制状态作用：$A2D7 STA $0501, $A2DC STA $0500, $A2FE INC $0501。

完整流程：[原始指令与调用链](handlers/state-03-sub-01.asm)；可执行逻辑在 program.json。

### 3/2 — bank12 $A30C / file $01831C

控制条件：$A313 BEQ→$A324 (否则$A315)。

控制状态作用：$A318 INC $0501。

完整流程：[原始指令与调用链](handlers/state-03-sub-02.asm)；可执行逻辑在 program.json。

### 3/3 — bank12 $A325 / file $018335

控制条件：$A328 BPL→$A367 (否则$A32A)。

控制状态作用：$A32C STA $007A。

完整流程：[原始指令与调用链](handlers/state-03-sub-03.asm)；可执行逻辑在 program.json。

## 4: 移动

### 4/0 — bank12 $A470 / file $018480

控制条件：无本地条件分支。

控制状态作用：$A475 INC $0501。

完整流程：[原始指令与调用链](handlers/state-04-sub-00.asm)；可执行逻辑在 program.json。

### 4/1 — bank12 $A47E / file $01848E

控制条件：$A4AF BEQ→$A4B4 (否则$A4B1)。

控制状态作用：$A4B1 INC $0501。

完整流程：[原始指令与调用链](handlers/state-04-sub-01.asm)；可执行逻辑在 program.json。

### 4/2 — bank12 $A4B5 / file $0184C5

控制条件：$A4C5 BPL→$A4D6 (否则$A4C7), $A4CC BNE→$A4D6 (否则$A4CE), $A4DB BEQ→$A504 (否则$A4DD), $A4F4 BNE→$A4FD (否则$A4F6), $A4FB BEQ→$A508 (否则$A4FD), $A502 BCC→$A4EF (否则$A504)。

控制状态作用：$A504 INC $0501, $A514 STA $0500, $A517 STA $0501。

完整流程：[原始指令与调用链](handlers/state-04-sub-02.asm)；可执行逻辑在 program.json。

### 4/3 — bank12 $A51F / file $01852F

控制条件：$A524 BNE→$A534 (否则$A526)。

控制状态作用：$A531 INC $0501。

完整流程：[原始指令与调用链](handlers/state-04-sub-03.asm)；可执行逻辑在 program.json。

### 4/4 — bank12 $A535 / file $018545

控制条件：$A53A BEQ→$A53D (否则$A53C), $A540 BEQ→$A545 (否则$A542), $A557 BPL→$A55B (否则$A559), $A58F BEQ→$A5AA (否则$A591), $A596 BPL→$A59A (否则$A598)。

控制状态作用：$A545 INC $0501, $A636 STA $0500, $A639 STA $0501。

完整流程：[原始指令与调用链](handlers/state-04-sub-04.asm)；可执行逻辑在 program.json。

### 4/5 — bank12 $A5CE / file $0185DE

控制条件：$A5DF BCC→$A616 (否则$A5E1), $A5E8 BEQ→$A616 (否则$A5EA), $A5EF BPL→$A5F3 (否则$A5F1), $A5FB BEQ→$A634 (否则$A5FD), $A609 BCC→$A634 (否则$A60B)。

控制状态作用：$A60B INC $0501, $A636 STA $0500, $A639 STA $0501。

完整流程：[原始指令与调用链](handlers/state-04-sub-05.asm)；可执行逻辑在 program.json。

### 4/6 — bank12 $A617 / file $018627

控制条件：$A61A BCC→$A63F (否则$A61C), $A623 BEQ→$A63F (否则$A625), $A62A BNE→$A640 (否则$A62C)。

控制状态作用：$A636 STA $0500, $A639 STA $0501。

完整流程：[原始指令与调用链](handlers/state-04-sub-06.asm)；可执行逻辑在 program.json。

## 5: 计略选择与效果

### 5/0 — bank12 $A89E / file $0188AE

控制条件：$A8B4 BPL→$A8AD (否则$A8B6)。

控制状态作用：$A8B6 INC $0501。

完整流程：[原始指令与调用链](handlers/state-05-sub-00.asm)；可执行逻辑在 program.json。

### 5/1 — bank12 $A8C1 / file $0188D1

控制条件：$A8C4 BCC→$A8D7 (否则$A8C6), $A8D2 BCC→$A8D7 (否则$A8D4)。

控制状态作用：$A8D4 INC $0501。

完整流程：[原始指令与调用链](handlers/state-05-sub-01.asm)；可执行逻辑在 program.json。

### 5/2 — bank12 $A8D8 / file $0188E8

控制条件：无本地条件分支。

控制状态作用：$A8DD INC $0501。

完整流程：[原始指令与调用链](handlers/state-05-sub-02.asm)；可执行逻辑在 program.json。

### 5/3 — bank12 $A917 / file $018927

控制条件：$A949 BCC→$A99F (否则$A94B), $A94F BEQ→$A968 (否则$A951), $A961 BCC→$A966 (否则$A963), $A96C BEQ→$A99F (否则$A96E), $A9C9 BNE→$A9D4 (否则$A9CB), $AA0B BCS→$AA29 (否则$AA0D), $AA10 BCS→$AA1D (否则$AA12)。

控制状态作用：$A994 STA $0501, $A999 STA $0500, $A9CE INC $0501, $A9D9 INC $0501, $AA14 STA $0501, $AA1D INC $0501。

完整流程：[原始指令与调用链](handlers/state-05-sub-03.asm)；可执行逻辑在 program.json。

### 5/4 — bank12 $A9DD / file $0189ED

控制条件：$A9E9 BCC→$AA28 (否则$A9EB), $A9EE BCS→$A9F6 (否则$A9F0), $A9F1 BCS→$AA23 (否则$A9F3), $A9FA BMI→$AA28 (否则$A9FC), $AA01 BNE→$AA28 (否则$AA03), $AA0B BCS→$AA29 (否则$AA0D), $AA10 BCS→$AA1D (否则$AA12)。

控制状态作用：$AA14 STA $0501, $AA1D INC $0501, $AA25 STA $0501。

完整流程：[原始指令与调用链](handlers/state-05-sub-04.asm)；可执行逻辑在 program.json。

### 5/5 — bank12 $AA2E / file $018A3E

控制条件：$AA37 BCC→$AA6B (否则$AA39), $AA3D BEQ→$AA6B (否则$AA3F)。

控制状态作用：$AA3F INC $0501。

完整流程：[原始指令与调用链](handlers/state-05-sub-05.asm)；可执行逻辑在 program.json。

### 5/6 — bank12 $AA6C / file $018A7C

控制条件：$AA6F BNE→$AAA6 (否则$AA71)。

控制状态作用：此入口不直接修改主/子/global状态。

完整流程：[原始指令与调用链](handlers/state-05-sub-06.asm)；可执行逻辑在 program.json。

### 5/7 — bank12 $AAA7 / file $018AB7

控制条件：$AAAA BNE→$AAE2 (否则$AAAC), $AAC1 BCC→$AAE2 (否则$AAC3), $AAC9 BEQ→$AAE3 (否则$AACB), $AAF0 BEQ→$AB02 (否则$AAF2), $AAF4 BNE→$AB11 (否则$AAF6), $AAF9 BNE→$AB02 (否则$AAFB), $AAFE BNE→$AB02 (否则$AB00), $AB07 BEQ→$AB11 (否则$AB09)。

控制状态作用：$AAC3 INC $0501。

完整流程：[原始指令与调用链](handlers/state-05-sub-07.asm)；可执行逻辑在 program.json。

### 5/8 — bank12 $AB2A / file $018B3A

控制条件：$AB2D BCC→$AB51 (否则$AB2F), $AB36 BEQ→$AB51 (否则$AB38), $AB44 BCC→$AB6F (否则$AB46), $AB78 BPL→$AB71 (否则$AB7A)。

控制状态作用：$AB46 INC $0501, $AB7C STA $0501, $AB7F STA $0500。

完整流程：[原始指令与调用链](handlers/state-05-sub-08.asm)；可执行逻辑在 program.json。

### 5/9 — bank12 $AB52 / file $018B62

控制条件：$AB55 BCC→$AB85 (否则$AB57), $AB5E BEQ→$AB85 (否则$AB60), $AB65 BNE→$AB86 (否则$AB67), $AB78 BPL→$AB71 (否则$AB7A)。

控制状态作用：$AB7C STA $0501, $AB7F STA $0500。

完整流程：[原始指令与调用链](handlers/state-05-sub-09.asm)；可执行逻辑在 program.json。

### 5/10 — bank12 $AB90 / file $018BA0

控制条件：$AB93 BCC→$ABA3 (否则$AB95), $AB9C BEQ→$ABA3 (否则$AB9E)。

控制状态作用：$ABA0 STA $0501。

完整流程：[原始指令与调用链](handlers/state-05-sub-10.asm)；可执行逻辑在 program.json。

## 6: 退却

### 6/0 — bank12 $B964 / file $019974

控制条件：无本地条件分支。

控制状态作用：$B969 INC $0501。

完整流程：[原始指令与调用链](handlers/state-06-sub-00.asm)；可执行逻辑在 program.json。

### 6/1 — bank12 $B96D / file $01997D

控制条件：$B976 BCC→$B9B5 (否则$B978), $B97C BEQ→$B98B (否则$B97E), $B98F BEQ→$B9B5 (否则$B991), $B9A9 BNE→$B9B5 (否则$B9AB)。

控制状态作用：$B980 STA $0501, $B985 STA $0500, $B991 INC $0501, $B9AD STA $0501。

完整流程：[原始指令与调用链](handlers/state-06-sub-01.asm)；可执行逻辑在 program.json。

### 6/2 — bank12 $B9B6 / file $0199C6

控制条件：$B9E7 BCC→$B9B5 (否则$B9E9), $B9ED BEQ→$B9FC (否则$B9EF), $BA00 BEQ→$BA19 (否则$BA02), $BA0D BCC→$BA1A (否则$BA0F), $BA20 BEQ→$BA26 (否则$BA22), $BA24 BNE→$BA2B (否则$BA26)。

控制状态作用：$B9F1 STA $0501, $B9F6 STA $0500, $BA11 STA $0501, $BA1A INC $0501。

完整流程：[原始指令与调用链](handlers/state-06-sub-02.asm)；可执行逻辑在 program.json。

### 6/3 — bank12 $BA30 / file $019A40

控制条件：$BA39 BCC→$BA63 (否则$BA3B), $BA3F BEQ→$BA4E (否则$BA41), $BA52 BEQ→$BA63 (否则$BA54)。

控制状态作用：$BA43 STA $0501, $BA48 STA $0500, $BA54 INC $0501。

完整流程：[原始指令与调用链](handlers/state-06-sub-03.asm)；可执行逻辑在 program.json。

### 6/4 — bank12 $BA64 / file $019A74

控制条件：$BA67 BCC→$BA82 (否则$BA69), $BA70 BEQ→$BA82 (否则$BA72)。

控制状态作用：$BA77 STA $0501, $BA7C STA $0500。

完整流程：[原始指令与调用链](handlers/state-06-sub-04.asm)；可执行逻辑在 program.json。

### 6/5 — bank12 $BA83 / file $019A93

控制条件：$BA86 BCC→$BA9E (否则$BA88), $BA8F BEQ→$BA9E (否则$BA91)。

控制状态作用：$BA93 STA $0501, $BA98 STA $0500。

完整流程：[原始指令与调用链](handlers/state-06-sub-05.asm)；可执行逻辑在 program.json。

## 7: 待機

### 7/0 — bank12 $BCB3 / file $019CC3

控制条件：无本地条件分支。

控制状态作用：$BCBD INC $0501。

完整流程：[原始指令与调用链](handlers/state-07-sub-00.asm)；可执行逻辑在 program.json。

### 7/1 — bank12 $BCC1 / file $019CD1

控制条件：$BCC4 BCC→$BCEC (否则$BCC6), $BCCD BEQ→$BCDC (否则$BCCF), $BCE0 BEQ→$BCEC (否则$BCE2)。

控制状态作用：$BCD1 STA $0501, $BCD6 STA $0500, $BCE4 STA $0501。

完整流程：[原始指令与调用链](handlers/state-07-sub-01.asm)；可执行逻辑在 program.json。

### 7/2 — bank12 $BCF6 / file $019D06

控制条件：无本地条件分支。

控制状态作用：$BD0A INC $0501。

完整流程：[原始指令与调用链](handlers/state-07-sub-02.asm)；可执行逻辑在 program.json。

### 7/3 — bank12 $BD13 / file $019D23

控制条件：$BD16 BCC→$BD2B (否则$BD18), $BD1F BEQ→$BD2B (否则$BD21)。

控制状态作用：$BD23 STA $0500, $BD28 STA $0501。

完整流程：[原始指令与调用链](handlers/state-07-sub-03.asm)；可执行逻辑在 program.json。

### 7/4 — bank12 $BD2C / file $019D3C

控制条件：$BD3B BCC→$BD40 (否则$BD3D)。

控制状态作用：$BD3D INC $0501。

完整流程：[原始指令与调用链](handlers/state-07-sub-04.asm)；可执行逻辑在 program.json。

### 7/5 — bank12 $BD41 / file $019D51

控制条件：$BD44 BNE→$BD49 (否则$BD46), $BD51 BEQ→$BD56 (否则$BD53), $BD5E BCS→$BD63 (否则$BD60)。

控制状态作用：$A20E STA $0501, $A211 STA $0500, $BD63 INC $0501。

完整流程：[原始指令与调用链](handlers/state-07-sub-05.asm)；可执行逻辑在 program.json。

### 7/6 — bank12 $BD6F / file $019D7F

控制条件：$BD72 BCC→$BD8E (否则$BD74), $BD7B BEQ→$BD8E (否则$BD7D), $BD82 BEQ→$BD8F (否则$BD84)。

控制状态作用：$A20E STA $0501, $A211 STA $0500。

完整流程：[原始指令与调用链](handlers/state-07-sub-06.asm)；可执行逻辑在 program.json。

### 7/7 — bank12 $BCED / file $019CFD

控制条件：$BCF0 BCC→$BCF5 (否则$BCF2), $BDC3 BPL→$BDCA (否则$BDC5), $BDE5 BEQ→$BE33 (否则$BDE7), $BE14 BEQ→$BE21 (否则$BE16), $BE5F BEQ→$BE67 (否则$BE61)。

控制状态作用：$BE18 STA $0500, $BE1D STA $0501, $BE70 STA $0501, $BE75 STA $0500。

完整流程：[原始指令与调用链](handlers/state-07-sub-07.asm)；可执行逻辑在 program.json。

## 8: 电脑方行动桥接

### 8/0 — bank12 $BEA6 / file $019EB6

控制条件：$BEA9 BPL→$BEB9 (否则$BEAB)。

控制状态作用：$BEB6 INC $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-00.asm)；可执行逻辑在 program.json。

### 8/1 — bank12 $BEBA / file $019ECA

控制条件：$BEBF BNE→$BF00 (否则$BEC1), $BEC6 BEQ→$BEFD (否则$BEC8), $BEF6 BNE→$BF00 (否则$BEF8), $BEFB BNE→$BF00 (否则$BEFD)。

控制状态作用：$BEFD INC $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-01.asm)；可执行逻辑在 program.json。

### 8/2 — bank12 $BF01 / file $019F11

控制条件：$BF0C BNE→$BF13 (否则$BF0E)。

控制状态作用：$BF07 STA $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-02.asm)；可执行逻辑在 program.json。

### 8/3 — bank12 $BF19 / file $019F29

控制条件：$BF1C BEQ→$BF1F (否则$BF1E), $BF35 BNE→$BF3B (否则$BF37), $BF60 BNE→$BF78 (否则$BF62), $BF64 BMI→$BF6F (否则$BF66)。

控制状态作用：$BF78 INC $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-03.asm)；可执行逻辑在 program.json。

### 8/4 — bank12 $BF7C / file $019F8C

控制条件：无本地条件分支。

控制状态作用：$BF8F STA $0500, $BF94 STA $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-04.asm)；可执行逻辑在 program.json。

### 8/5 — bank12 $BF98 / file $019FA8

控制条件：无本地条件分支。

控制状态作用：$BFB0 INC $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-05.asm)；可执行逻辑在 program.json。

### 8/6 — bank12 $BFB8 / file $019FC8

控制条件：$BFCA BCC→$BFDB (否则$BFCC), $BFD3 BEQ→$BFDB (否则$BFD5)。

控制状态作用：$BFD5 INC $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-06.asm)；可执行逻辑在 program.json。

### 8/7 — bank12 $BFDC / file $019FEC

控制条件：$A3EF BMI→$A406 (否则$A3F1), $BFE5 BPL→$C003 (否则$BFE7)。

控制状态作用：$BFF5 STA $0500, $BFF8 STA $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-07.asm)；可执行逻辑在 program.json。

### 8/8 — bank13 $C004 / file $01A014

控制条件：$C009 BNE→$C00E (否则$C00B)。

控制状态作用：$C040 INC $0501, $C1F2 STA $0500, $C1F5 STA $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-08.asm)；可执行逻辑在 program.json。

### 8/9 — bank13 $C054 / file $01A064

控制条件：$C06E BCC→$C07C (否则$C070), $C077 BEQ→$C07C (否则$C079)。

控制状态作用：$C079 INC $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-09.asm)；可执行逻辑在 program.json。

### 8/10 — bank13 $C07D / file $01A08D

控制条件：$C0B2 BEQ→$C0BE (否则$C0B4), $C0CB BEQ→$C0FB (否则$C0CD), $C0CF BEQ→$C0E1 (否则$C0D1), $C0D3 BNE→$C0F5 (否则$C0D5), $C0D8 BNE→$C0E1 (否则$C0DA), $C0DD BNE→$C0E1 (否则$C0DF), $C0E6 BEQ→$C0F5 (否则$C0E8)。

控制状态作用：$C0AC STA $0501, $C0ED STA $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-10.asm)；可执行逻辑在 program.json。

### 8/11 — bank13 $C110 / file $01A120

控制条件：$C122 BCC→$C13A (否则$C124), $C12B BEQ→$C13A (否则$C12D)。

控制状态作用：$C137 STA $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-11.asm)；可执行逻辑在 program.json。

### 8/12 — bank13 $C13B / file $01A14B

控制条件：$BDC3 BPL→$BDCA (否则$BDC5), $BDE5 BEQ→$BE33 (否则$BDE7), $BE14 BEQ→$BE21 (否则$BE16), $BE5F BEQ→$BE67 (否则$BE61), $C13E BCC→$C13A (否则$C140)。

控制状态作用：$BE18 STA $0500, $BE1D STA $0501, $BE70 STA $0501, $BE75 STA $0500。

完整流程：[原始指令与调用链](handlers/state-08-sub-12.asm)；可执行逻辑在 program.json。

### 8/13 — bank13 $C149 / file $01A159

控制条件：$C14E BMI→$C152 (否则$C150)。

控制状态作用：$C170 INC $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-13.asm)；可执行逻辑在 program.json。

### 8/14 — bank13 $C178 / file $01A188

控制条件：$C189 BCC→$C13A (否则$C18B), $C192 BEQ→$C1AE (否则$C194)。

控制状态作用：$C1AB STA $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-14.asm)；可执行逻辑在 program.json。

### 8/15 — bank13 $C1D1 / file $01A1E1

控制条件：$C1D4 BCC→$C1EA (否则$C1D6), $C1DD BEQ→$C1EA (否则$C1DF)。

控制状态作用：$C1E7 INC $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-15.asm)；可执行逻辑在 program.json。

### 8/16 — bank13 $C1EB / file $01A1FB

控制条件：$C1EE BCC→$C1FB (否则$C1F0)。

控制状态作用：$C1F2 STA $0500, $C1F5 STA $0501。

完整流程：[原始指令与调用链](handlers/state-08-sub-16.asm)；可执行逻辑在 program.json。

## 9: 村落服务跨银行入口

### 9/0 — bank13 $C1FC / file $01A20C

控制条件：无本地条件分支。

控制状态作用：此入口不直接修改主/子/global状态。

完整流程：[原始指令与调用链](handlers/state-09-sub-00.asm)；可执行逻辑在 program.json。

## 10: 下一方回合准备

### 10/0 — bank13 $C218 / file $01A228

控制条件：无本地条件分支。

控制状态作用：$C21B INC $0501。

完整流程：[原始指令与调用链](handlers/state-10-sub-00.asm)；可执行逻辑在 program.json。

### 10/1 — bank13 $C24F / file $01A25F

控制条件：$C25D BEQ→$C286 (否则$C25F)。

控制状态作用：$C264 STA $0501, $C286 INC $0501。

完整流程：[原始指令与调用链](handlers/state-10-sub-01.asm)；可执行逻辑在 program.json。

### 10/2 — bank13 $C28A / file $01A29A

控制条件：$C29C BEQ→$C2C9 (否则$C29E)。

控制状态作用：$C2A3 STA $0501, $C2C9 INC $0501。

完整流程：[原始指令与调用链](handlers/state-10-sub-02.asm)；可执行逻辑在 program.json。

### 10/3 — bank13 $C2CD / file $01A2DD

控制条件：无本地条件分支。

控制状态作用：$C2CF STA $0500, $C2D4 STA $0501。

完整流程：[原始指令与调用链](handlers/state-10-sub-03.asm)；可执行逻辑在 program.json。

### 10/4 — bank13 $C2F7 / file $01A307

控制条件：$C2FA BCC→$C30D (否则$C2FC), $C303 BEQ→$C30D (否则$C305)。

控制状态作用：$C305 INC $0501。

完整流程：[原始指令与调用链](handlers/state-10-sub-04.asm)；可执行逻辑在 program.json。

### 10/5 — bank13 $C30E / file $01A31E

控制条件：$C316 BCC→$C328 (否则$C318), $C330 BNE→$C338 (否则$C332)。

控制状态作用：$C31F STA $0501, $C349 INC $0501。

完整流程：[原始指令与调用链](handlers/state-10-sub-05.asm)；可执行逻辑在 program.json。

### 10/6 — bank13 $C350 / file $01A360

控制条件：$C38F BNE→$C3CA (否则$C391), $C394 BNE→$C3CA (否则$C396), $C3A9 BNE→$C3CA (否则$C3AB), $C3B1 BCC→$C3CA (否则$C3B3), $C3B7 BCS→$C3CA (否则$C3B9), $C3BB BEQ→$C3CA (否则$C3BD)。

控制状态作用：$C3BD DEC $0501。

完整流程：[原始指令与调用链](handlers/state-10-sub-06.asm)；可执行逻辑在 program.json。

## 11: 单挑后升级提示

### 11/0 — bank13 $C69F / file $01A6AF

控制条件：$C6F1 BEQ→$C6F5 (否则$C6F3), $C709 BEQ→$C712 (否则$C70B), $C710 BEQ→$C716 (否则$C712), $C724 BEQ→$C712 (否则$C726), $C754 BNE→$C758 (否则$C756)。

控制状态作用：$C712 INC $0501, $C744 STA $0501。

完整流程：[原始指令与调用链](handlers/state-11-sub-00.asm)；可执行逻辑在 program.json。

### 11/1 — bank13 $C6AC / file $01A6BC

控制条件：$C6F1 BEQ→$C6F5 (否则$C6F3), $C709 BEQ→$C712 (否则$C70B), $C710 BEQ→$C716 (否则$C712), $C724 BEQ→$C712 (否则$C726), $C754 BNE→$C758 (否则$C756)。

控制状态作用：$C712 INC $0501, $C744 STA $0501。

完整流程：[原始指令与调用链](handlers/state-11-sub-01.asm)；可执行逻辑在 program.json。

### 11/2 — bank13 $C6B9 / file $01A6C9

控制条件：无本地条件分支。

控制状态作用：$A20E STA $0501, $A211 STA $0500。

完整流程：[原始指令与调用链](handlers/state-11-sub-02.asm)；可执行逻辑在 program.json。

### 11/3 — bank13 $C6BC / file $01A6CC

控制条件：$C6BF BCC→$C6DF (否则$C6C1), $C6C8 BEQ→$C6DF (否则$C6CA), $C6CF BNE→$C6E0 (否则$C6D1)。

控制状态作用：$C6DC STA $0501。

完整流程：[原始指令与调用链](handlers/state-11-sub-03.asm)；可执行逻辑在 program.json。

## 12: 战斗结果确认

### 12/0 — bank13 $C99E / file $01A9AE

控制条件：无本地条件分支。

控制状态作用：$C9A9 INC $0501。

完整流程：[原始指令与调用链](handlers/state-12-sub-00.asm)；可执行逻辑在 program.json。

### 12/1 — bank13 $C9AD / file $01A9BD

控制条件：$C9B0 BCC→$C9C2 (否则$C9B2), $C9B5 BNE→$C9C2 (否则$C9B7)。

控制状态作用：$C9B7 INC $0501。

完整流程：[原始指令与调用链](handlers/state-12-sub-01.asm)；可执行逻辑在 program.json。

### 12/2 — bank13 $C9C3 / file $01A9D3

控制条件：$C9C6 BNE→$C9C2 (否则$C9C8), $C9E8 BPL→$C9E4 (否则$C9EA)。

控制状态作用：$C9F2 INC $0501。

完整流程：[原始指令与调用链](handlers/state-12-sub-02.asm)；可执行逻辑在 program.json。

### 12/3 — bank13 $C9FE / file $01AA0E

控制条件：$CA04 BCC→$CA12 (否则$CA06), $CA0D BEQ→$CA12 (否则$CA0F)。

控制状态作用：$CA0F INC $0501。

完整流程：[原始指令与调用链](handlers/state-12-sub-03.asm)；可执行逻辑在 program.json。

### 12/4 — bank13 $CA13 / file $01AA23

控制条件：$CA19 BCC→$CA26 (否则$CA1B)。

控制状态作用：$CA1D STA $0500, $CA22 STA $0501, $CA26 INC $0501。

完整流程：[原始指令与调用链](handlers/state-12-sub-04.asm)；可执行逻辑在 program.json。

### 12/5 — bank13 $CA2F / file $01AA3F

控制条件：$CA35 BCC→$CA40 (否则$CA37), $CA3B BEQ→$CA40 (否则$CA3D)。

控制状态作用：$CA3D DEC $0501。

完整流程：[原始指令与调用链](handlers/state-12-sub-05.asm)；可执行逻辑在 program.json。

## 13: 败方武将转移或转为在野

### 13/0 — bank13 $CD2A / file $01AD3A

控制条件：$CD36 BNE→$CD46 (否则$CD38)。

控制状态作用：$CD3D STA $0501, $CD42 STA $0500, $CD4E INC $0501。

完整流程：[原始指令与调用链](handlers/state-13-sub-00.asm)；可执行逻辑在 program.json。

### 13/1 — bank13 $CD52 / file $01AD62

控制条件：$CD58 BCC→$CD63 (否则$CD5A), $CD61 BNE→$CD64 (否则$CD63), $CD83 BEQ→$CD9C (否则$CD85), $CD91 BCS→$CD99 (否则$CD93), $CD9A BPL→$CD8C (否则$CD9C), $CDA4 BEQ→$CDAA (否则$CDA6), $CDBF BCS→$CDDB (否则$CDC1), $CDC3 BEQ→$CDE3 (否则$CDC5)。

控制状态作用：$CD3D STA $0501, $CD42 STA $0500, $CD64 INC $0501, $CDDD STA $0501。

完整流程：[原始指令与调用链](handlers/state-13-sub-01.asm)；可执行逻辑在 program.json。

### 13/2 — bank13 $CDF2 / file $01AE02

控制条件：$CE23 BCC→$CE55 (否则$CE25), $CE29 BEQ→$CE55 (否则$CE2B), $CE38 BEQ→$CE41 (否则$CE3A), $CE3F BCS→$CE55 (否则$CE41), $CE4B BNE→$CE4F (否则$CE4D)。

控制状态作用：$CE41 INC $0501。

完整流程：[原始指令与调用链](handlers/state-13-sub-02.asm)；可执行逻辑在 program.json。

### 13/3 — bank13 $CE56 / file $01AE66

控制条件：$CE5C BCC→$CE75 (否则$CE5E), $CE65 BEQ→$CE75 (否则$CE67)。

控制状态作用：$CE72 INC $0501。

完整流程：[原始指令与调用链](handlers/state-13-sub-03.asm)；可执行逻辑在 program.json。

### 13/4 — bank13 $CE76 / file $01AE86

控制条件：$CE7C BCC→$CE9D (否则$CE7E)。

控制状态作用：$CE8C INC $0501。

完整流程：[原始指令与调用链](handlers/state-13-sub-04.asm)；可执行逻辑在 program.json。

### 13/5 — bank13 $CE9E / file $01AEAE

控制条件：$CD36 BNE→$CD46 (否则$CD38), $CED6 BEQ→$CF03 (否则$CED8), $CEDE BNE→$CF03 (否则$CEE0), $CEE7 BMI→$CEEA (否则$CEE9), $CEED BCC→$CEE4 (否则$CEEF), $CEF0 BEQ→$CF1A (否则$CEF2), $CEF9 BNE→$CEFD (否则$CEFB)。

控制状态作用：$CD3D STA $0501, $CD42 STA $0500, $CD4E INC $0501, $CF00 INC $0501, $CF2A STA $0501。

完整流程：[原始指令与调用链](handlers/state-13-sub-05.asm)；可执行逻辑在 program.json。

### 13/6 — bank13 $CF09 / file $01AF19

控制条件：$CD36 BNE→$CD46 (否则$CD38), $CF0F BCC→$CF33 (否则$CF11), $CF18 BEQ→$CF33 (否则$CF1A)。

控制状态作用：$CD3D STA $0501, $CD42 STA $0500, $CD4E INC $0501, $CF2A STA $0501。

完整流程：[原始指令与调用链](handlers/state-13-sub-06.asm)；可执行逻辑在 program.json。

## 14: 胜方收容及超额武将转移

### 14/0 — bank13 $D2E1 / file $01B2F1

控制条件：$D2F1 BCS→$D304 (否则$D2F3)。

控制状态作用：$D2F8 STA $0500, $D300 STA $0501, $D30C INC $0501。

完整流程：[原始指令与调用链](handlers/state-14-sub-00.asm)；可执行逻辑在 program.json。

### 14/1 — bank13 $D310 / file $01B320

控制条件：$D316 BCC→$D34A (否则$D318), $D31F BEQ→$D34A (否则$D321)。

控制状态作用：$D321 INC $0501。

完整流程：[原始指令与调用链](handlers/state-14-sub-01.asm)；可执行逻辑在 program.json。

### 14/2 — bank13 $D34B / file $01B35B

控制条件：$D37C BCC→$D34A (否则$D37E), $D382 BEQ→$D3AE (否则$D384), $D391 BEQ→$D39A (否则$D393), $D398 BCS→$D3AE (否则$D39A), $D3A4 BNE→$D3A8 (否则$D3A6)。

控制状态作用：$D39A INC $0501。

完整流程：[原始指令与调用链](handlers/state-14-sub-02.asm)；可执行逻辑在 program.json。

### 14/3 — bank13 $D3AF / file $01B3BF

控制条件：$D3B5 BCC→$D3D6 (否则$D3B7), $D3BE BEQ→$D3D6 (否则$D3C0)。

控制状态作用：$D3D3 INC $0501。

完整流程：[原始指令与调用链](handlers/state-14-sub-03.asm)；可执行逻辑在 program.json。

### 14/4 — bank13 $D3D7 / file $01B3E7

控制条件：$D3DD BCC→$D3F6 (否则$D3DF)。

控制状态作用：$D3ED INC $0501。

完整流程：[原始指令与调用链](handlers/state-14-sub-04.asm)；可执行逻辑在 program.json。

### 14/5 — bank13 $D3F7 / file $01B407

控制条件：$D2F1 BCS→$D304 (否则$D2F3), $D42F BEQ→$D45C (否则$D431), $D437 BNE→$D45C (否则$D439), $D440 BMI→$D443 (否则$D442), $D446 BCC→$D43D (否则$D448), $D449 BEQ→$D473 (否则$D44B), $D452 BNE→$D456 (否则$D454)。

控制状态作用：$D2F8 STA $0500, $D300 STA $0501, $D30C INC $0501, $D459 INC $0501, $D483 STA $0501。

完整流程：[原始指令与调用链](handlers/state-14-sub-05.asm)；可执行逻辑在 program.json。

### 14/6 — bank13 $D462 / file $01B472

控制条件：$D2F1 BCS→$D304 (否则$D2F3), $D468 BCC→$D48C (否则$D46A), $D471 BEQ→$D48C (否则$D473)。

控制状态作用：$D2F8 STA $0500, $D300 STA $0501, $D30C INC $0501, $D483 STA $0501。

完整流程：[原始指令与调用链](handlers/state-14-sub-06.asm)；可执行逻辑在 program.json。

## 15: 归属结算与返回城市

### 15/0 — bank13 $D4F0 / file $01B500

实际委托 bank8 $BAC1。可读语义见 `finalization_phase`；AI武将处理 BC46 仍为显式依赖。

控制条件：无本地条件分支。

控制状态作用：此入口不直接修改主/子/global状态。

完整流程：[原始指令与调用链](handlers/state-15-sub-00.asm)；可执行逻辑在 program.json。

### 15/1 — bank13 $D4F0 / file $01B500

实际委托 bank8 $BB3D。可读语义见 `finalization_phase`；AI武将处理 BC46 仍为显式依赖。

控制条件：无本地条件分支。

控制状态作用：此入口不直接修改主/子/global状态。

完整流程：[原始指令与调用链](handlers/state-15-sub-01.asm)；可执行逻辑在 program.json。

### 15/2 — bank13 $D4F0 / file $01B500

实际委托 bank8 $BB93。可读语义见 `finalization_phase`；AI武将处理 BC46 仍为显式依赖。

控制条件：无本地条件分支。

控制状态作用：此入口不直接修改主/子/global状态。

完整流程：[原始指令与调用链](handlers/state-15-sub-02.asm)；可执行逻辑在 program.json。

### 15/3 — bank13 $D4F0 / file $01B500

实际委托 bank8 $BBA0。可读语义见 `finalization_phase`；AI武将处理 BC46 仍为显式依赖。

控制条件：无本地条件分支。

控制状态作用：此入口不直接修改主/子/global状态。

完整流程：[原始指令与调用链](handlers/state-15-sub-03.asm)；可执行逻辑在 program.json。

