; main=8 sub=5: 电脑方行动桥接
; entry bank12 $BF98; file $019FA8
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019FA8 b12:$BF98 AD 8D 6F       LDA  $6F8D
019FAB b12:$BF9B 8D 09 05       STA  $0509
019FAE b12:$BF9E A0 3D          LDY  #$3D
019FB0 b12:$BFA0 20 07 EE       JSR  $EE07 ; far_A027
; inline .word $A027, resumes $BFA5
019FB5 b12:$BFA5 A9 02          LDA  #$02
019FB7 b12:$BFA7 8D A4 00       STA  $00A4
019FBA b12:$BFAA CE 05 05       DEC  $0505
019FBD b12:$BFAD CE 05 05       DEC  $0505
019FC0 b12:$BFB0 EE 01 05       INC  $0501
019FC3 b12:$BFB3 A9 A0          LDA  #$A0
019FC5 b12:$BFB5 4C 83 F2       JMP  $F283 ; queue_message_job_1
