; main=14 sub=0: 胜方收容及超额武将转移
; entry bank13 $D2E1; file $01B2F1
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01B2F1 b13:$D2E1 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01B2F4 b13:$D2E4 20 E1 D0       JSR  $D0E1 ; select_next_postbattle_officer
01B2F7 b13:$D2E7 A9 FF          LDA  #$FF
01B2F9 b13:$D2E9 9D 2C 04       STA  $042C,X
01B2FC b13:$D2EC 8E 0A 05       STX  $050A
01B2FF b13:$D2EF E0 0B          CPX  #$0B
01B301 b13:$D2F1 B0 11          BCS  $D304
01B303 b13:$D2F3 20 8D D4       JSR  $D48D ; postbattle_removal_operation
01B306 b13:$D2F6 A9 0F          LDA  #$0F
01B308 b13:$D2F8 8D 00 05       STA  $0500
01B30B b13:$D2FB AD 0B 05       LDA  $050B
01B30E b13:$D2FE 29 0F          AND  #$0F
01B310 b13:$D300 8D 01 05       STA  $0501
01B313 b13:$D303 60             RTS
01B314 b13:$D304 A9 DF          LDA  #$DF
01B316 b13:$D306 20 93 F2       JSR  $F293 ; queue_message_job_0
01B319 b13:$D309 20 C3 D0       JSR  $D0C3 ; cpu_D0C3
01B31C b13:$D30C EE 01 05       INC  $0501
01B31F b13:$D30F 60             RTS
