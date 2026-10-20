; main=6 sub=3: 退却
; entry bank12 $BA30; file $019A40
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018207 b12:$A1F7 A9 05          LDA  #$05
018209 b12:$A1F9 20 93 F2       JSR  $F293 ; queue_message_job_0
01820C b12:$A1FC A9 01          LDA  #$01
01820E b12:$A1FE 85 12          STA  $12
018210 b12:$A200 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
018213 b12:$A203 A9 00          LDA  #$00
018215 b12:$A205 8D 24 04       STA  $0424
018218 b12:$A208 8D 25 04       STA  $0425
01821B b12:$A20B 60             RTS
019A40 b12:$BA30 20 70 DC       JSR  $DC70 ; dialog_navigation
019A43 b12:$BA33 20 DE A1       JSR  $A1DE ; blink_menu_cursor
019A46 b12:$BA36 20 27 DF       JSR  $DF27 ; text_jobs_idle
019A49 b12:$BA39 90 28          BCC  $BA63
019A4B b12:$BA3B A5 81          LDA  $81
019A4D b12:$BA3D 29 02          AND  #$02
019A4F b12:$BA3F F0 0D          BEQ  $BA4E
019A51 b12:$BA41 A9 00          LDA  #$00
019A53 b12:$BA43 8D 01 05       STA  $0501
019A56 b12:$BA46 A9 00          LDA  #$00
019A58 b12:$BA48 8D 00 05       STA  $0500
019A5B b12:$BA4B 4C F7 A1       JMP  $A1F7
019A5E b12:$BA4E A5 81          LDA  $81
019A60 b12:$BA50 29 01          AND  #$01
019A62 b12:$BA52 F0 0F          BEQ  $BA63
019A64 b12:$BA54 EE 01 05       INC  $0501
019A67 b12:$BA57 A9 00          LDA  #$00
019A69 b12:$BA59 85 12          STA  $12
019A6B b12:$BA5B 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
019A6E b12:$BA5E A9 D8          LDA  #$D8
019A70 b12:$BA60 20 93 F2       JSR  $F293 ; queue_message_job_0
019A73 b12:$BA63 60             RTS
