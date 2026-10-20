; main=11 sub=2: 单挑后升级提示
; entry bank13 $C6B9; file $01A6C9
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01821C b12:$A20C A9 00          LDA  #$00
01821E b12:$A20E 8D 01 05       STA  $0501
018221 b12:$A211 8D 00 05       STA  $0500
018224 b12:$A214 8D 24 04       STA  $0424
018227 b12:$A217 8D 25 04       STA  $0425
01822A b12:$A21A 60             RTS
01A6C9 b13:$C6B9 4C 0C A2       JMP  $A20C
