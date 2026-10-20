; main=6 sub=4: 退却
; entry bank12 $BA64; file $019A74
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
019A74 b12:$BA64 20 27 DF       JSR  $DF27 ; text_jobs_idle
019A77 b12:$BA67 90 19          BCC  $BA82
019A79 b12:$BA69 20 70 DC       JSR  $DC70 ; dialog_navigation
019A7C b12:$BA6C A5 81          LDA  $81
019A7E b12:$BA6E 29 01          AND  #$01
019A80 b12:$BA70 F0 10          BEQ  $BA82
019A82 b12:$BA72 20 2A BC       JSR  $BC2A ; cpu_BC2A
019A85 b12:$BA75 A9 00          LDA  #$00
019A87 b12:$BA77 8D 01 05       STA  $0501
019A8A b12:$BA7A A9 00          LDA  #$00
019A8C b12:$BA7C 8D 00 05       STA  $0500
019A8F b12:$BA7F 4C F7 A1       JMP  $A1F7
019A92 b12:$BA82 60             RTS
