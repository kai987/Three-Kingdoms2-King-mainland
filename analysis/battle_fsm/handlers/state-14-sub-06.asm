; main=14 sub=6: 胜方收容及超额武将转移
; entry bank13 $D462; file $01B472
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
01B472 b13:$D462 20 BC D1       JSR  $D1BC ; cpu_D1BC
01B475 b13:$D465 20 27 DF       JSR  $DF27 ; text_jobs_idle
01B478 b13:$D468 90 22          BCC  $D48C
01B47A b13:$D46A 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01B47D b13:$D46D A5 81          LDA  $81
01B47F b13:$D46F 29 01          AND  #$01
01B481 b13:$D471 F0 19          BEQ  $D48C
01B483 b13:$D473 A9 E1          LDA  #$E1
01B485 b13:$D475 85 E6          STA  $E6
01B487 b13:$D477 85 E7          STA  $E7
01B489 b13:$D479 A9 00          LDA  #$00
01B48B b13:$D47B 85 8E          STA  $8E
01B48D b13:$D47D A9 50          LDA  #$50
01B48F b13:$D47F 85 90          STA  $90
01B491 b13:$D481 A9 00          LDA  #$00
01B493 b13:$D483 8D 01 05       STA  $0501
01B496 b13:$D486 20 F9 D1       JSR  $D1F9 ; cpu_D1F9
01B499 b13:$D489 4C E1 D2       JMP  $D2E1
01B49C b13:$D48C 60             RTS
