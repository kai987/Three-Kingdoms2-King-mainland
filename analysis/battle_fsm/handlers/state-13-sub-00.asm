; main=13 sub=0: 败方武将转移或转为在野
; entry bank13 $CD2A; file $01AD3A
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AD3A b13:$CD2A 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AD3D b13:$CD2D 20 E1 D0       JSR  $D0E1 ; select_next_postbattle_officer
01AD40 b13:$CD30 A9 FF          LDA  #$FF
01AD42 b13:$CD32 9D 2C 04       STA  $042C,X
01AD45 b13:$CD35 8A             TXA
01AD46 b13:$CD36 D0 0E          BNE  $CD46
01AD48 b13:$CD38 AD 0B 05       LDA  $050B
01AD4B b13:$CD3B 29 0F          AND  #$0F
01AD4D b13:$CD3D 8D 01 05       STA  $0501
01AD50 b13:$CD40 A9 0F          LDA  #$0F
01AD52 b13:$CD42 8D 00 05       STA  $0500
01AD55 b13:$CD45 60             RTS
01AD56 b13:$CD46 A9 DC          LDA  #$DC
01AD58 b13:$CD48 20 93 F2       JSR  $F293 ; queue_message_job_0
01AD5B b13:$CD4B 20 C3 D0       JSR  $D0C3 ; cpu_D0C3
01AD5E b13:$CD4E EE 01 05       INC  $0501
01AD61 b13:$CD51 60             RTS
