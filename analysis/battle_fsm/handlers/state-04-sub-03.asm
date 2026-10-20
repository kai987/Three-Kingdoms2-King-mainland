; main=4 sub=3: 移动
; entry bank12 $A51F; file $01852F
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01852F b12:$A51F AD 8B 6F       LDA  $6F8B
018532 b12:$A522 C9 FF          CMP  #$FF
018534 b12:$A524 D0 0E          BNE  $A534
018536 b12:$A526 A9 01          LDA  #$01
018538 b12:$A528 8D 8B 6F       STA  $6F8B
01853B b12:$A52B AD 09 05       LDA  $0509
01853E b12:$A52E 8D 8C 6F       STA  $6F8C
018541 b12:$A531 EE 01 05       INC  $0501
018544 b12:$A534 60             RTS
