; main=5 sub=1: 计略选择与效果
; entry bank12 $A8C1; file $0188D1
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0188D1 b12:$A8C1 20 27 DF       JSR  $DF27 ; text_jobs_idle
0188D4 b12:$A8C4 90 11          BCC  $A8D7
0188D6 b12:$A8C6 20 D9 AB       JSR  $ABD9 ; cpu_ABD9
0188D9 b12:$A8C9 AD 0B 05       LDA  $050B
0188DC b12:$A8CC EE 0B 05       INC  $050B
0188DF b12:$A8CF CD 42 05       CMP  $0542
0188E2 b12:$A8D2 90 03          BCC  $A8D7
0188E4 b12:$A8D4 EE 01 05       INC  $0501
0188E7 b12:$A8D7 60             RTS
