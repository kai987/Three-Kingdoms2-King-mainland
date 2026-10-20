; main=1 sub=0: 单位信息
; entry bank12 $A227; file $018237
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018237 b12:$A227 EE 01 05       INC  $0501
01823A b12:$A22A A9 08          LDA  #$08
01823C b12:$A22C 85 BA          STA  $BA
01823E b12:$A22E A9 06          LDA  #$06
018240 b12:$A230 85 BB          STA  $BB
018242 b12:$A232 A9 00          LDA  #$00
018244 b12:$A234 8D 0C 04       STA  $040C
018247 b12:$A237 8D 0D 04       STA  $040D
01824A b12:$A23A AC 09 05       LDY  $0509
01824D b12:$A23D B9 64 06       LDA  $0664,Y
018250 b12:$A240 8D 10 04       STA  $0410
018253 b12:$A243 60             RTS
