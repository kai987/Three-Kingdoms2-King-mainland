; main=7 sub=1: 待機
; entry bank12 $BCC1; file $019CD1
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
019CD1 b12:$BCC1 20 27 DF       JSR  $DF27 ; text_jobs_idle
019CD4 b12:$BCC4 90 26          BCC  $BCEC
019CD6 b12:$BCC6 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
019CD9 b12:$BCC9 A5 81          LDA  $81
019CDB b12:$BCCB 29 02          AND  #$02
019CDD b12:$BCCD F0 0D          BEQ  $BCDC
019CDF b12:$BCCF A9 00          LDA  #$00
019CE1 b12:$BCD1 8D 01 05       STA  $0501
019CE4 b12:$BCD4 A9 00          LDA  #$00
019CE6 b12:$BCD6 8D 00 05       STA  $0500
019CE9 b12:$BCD9 4C F7 A1       JMP  $A1F7
019CEC b12:$BCDC A5 81          LDA  $81
019CEE b12:$BCDE 29 01          AND  #$01
019CF0 b12:$BCE0 F0 0A          BEQ  $BCEC
019CF2 b12:$BCE2 A9 07          LDA  #$07
019CF4 b12:$BCE4 8D 01 05       STA  $0501
019CF7 b12:$BCE7 A9 05          LDA  #$05
019CF9 b12:$BCE9 20 93 F2       JSR  $F293 ; queue_message_job_0
019CFC b12:$BCEC 60             RTS
