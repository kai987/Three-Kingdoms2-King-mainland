; main=5 sub=10: 计略选择与效果
; entry bank12 $AB90; file $018BA0
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018BA0 b12:$AB90 20 27 DF       JSR  $DF27 ; text_jobs_idle
018BA3 b12:$AB93 90 0E          BCC  $ABA3
018BA5 b12:$AB95 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
018BA8 b12:$AB98 A5 81          LDA  $81
018BAA b12:$AB9A 29 01          AND  #$01
018BAC b12:$AB9C F0 05          BEQ  $ABA3
018BAE b12:$AB9E A9 00          LDA  #$00
018BB0 b12:$ABA0 8D 01 05       STA  $0501
018BB3 b12:$ABA3 60             RTS
