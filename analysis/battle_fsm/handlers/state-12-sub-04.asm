; main=12 sub=4: 战斗结果确认
; entry bank13 $CA13; file $01AA23
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AA23 b13:$CA13 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AA26 b13:$CA16 20 51 CA       JSR  $CA51 ; result_yes_flag
01AA29 b13:$CA19 90 0B          BCC  $CA26
01AA2B b13:$CA1B A9 0F          LDA  #$0F
01AA2D b13:$CA1D 8D 00 05       STA  $0500
01AA30 b13:$CA20 A9 00          LDA  #$00
01AA32 b13:$CA22 8D 01 05       STA  $0501
01AA35 b13:$CA25 60             RTS
01AA36 b13:$CA26 EE 01 05       INC  $0501
01AA39 b13:$CA29 A9 D5          LDA  #$D5
01AA3B b13:$CA2B 20 93 F2       JSR  $F293 ; queue_message_job_0
01AA3E b13:$CA2E 60             RTS
