; main=2 sub=0: 普通攻击目标选择
; entry bank12 $A2A7; file $0182B7
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0182B7 b12:$A2A7 A9 C3          LDA  #$C3
0182B9 b12:$A2A9 20 83 F2       JSR  $F283 ; queue_message_job_1
0182BC b12:$A2AC EE 01 05       INC  $0501
0182BF b12:$A2AF AD 09 05       LDA  $0509
0182C2 b12:$A2B2 8D 0A 05       STA  $050A
0182C5 b12:$A2B5 A9 00          LDA  #$00
0182C7 b12:$A2B7 8D A4 00       STA  $00A4
0182CA b12:$A2BA 60             RTS
