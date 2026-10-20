; main=13 sub=6: 败方武将转移或转为在野
; entry bank13 $CF09; file $01AF19
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
01AF19 b13:$CF09 20 BC D1       JSR  $D1BC ; cpu_D1BC
01AF1C b13:$CF0C 20 27 DF       JSR  $DF27 ; text_jobs_idle
01AF1F b13:$CF0F 90 22          BCC  $CF33
01AF21 b13:$CF11 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01AF24 b13:$CF14 A5 81          LDA  $81
01AF26 b13:$CF16 29 01          AND  #$01
01AF28 b13:$CF18 F0 19          BEQ  $CF33
01AF2A b13:$CF1A A9 E1          LDA  #$E1
01AF2C b13:$CF1C 85 E6          STA  $E6
01AF2E b13:$CF1E 85 E7          STA  $E7
01AF30 b13:$CF20 A9 00          LDA  #$00
01AF32 b13:$CF22 85 8E          STA  $8E
01AF34 b13:$CF24 A9 50          LDA  #$50
01AF36 b13:$CF26 85 90          STA  $90
01AF38 b13:$CF28 A9 00          LDA  #$00
01AF3A b13:$CF2A 8D 01 05       STA  $0501
01AF3D b13:$CF2D 20 F9 D1       JSR  $D1F9 ; cpu_D1F9
01AF40 b13:$CF30 4C 2A CD       JMP  $CD2A
01AF43 b13:$CF33 60             RTS
