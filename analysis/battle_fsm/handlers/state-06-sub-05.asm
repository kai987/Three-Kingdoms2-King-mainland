; main=6 sub=5: 退却
; entry bank12 $BA83; file $019A93
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
019A93 b12:$BA83 20 27 DF       JSR  $DF27 ; text_jobs_idle
019A96 b12:$BA86 90 16          BCC  $BA9E
019A98 b12:$BA88 20 70 DC       JSR  $DC70 ; dialog_navigation
019A9B b12:$BA8B A5 81          LDA  $81
019A9D b12:$BA8D 29 01          AND  #$01
019A9F b12:$BA8F F0 0D          BEQ  $BA9E
019AA1 b12:$BA91 A9 00          LDA  #$00
019AA3 b12:$BA93 8D 01 05       STA  $0501
019AA6 b12:$BA96 A9 00          LDA  #$00
019AA8 b12:$BA98 8D 00 05       STA  $0500
019AAB b12:$BA9B 4C F7 A1       JMP  $A1F7
019AAE b12:$BA9E 60             RTS
