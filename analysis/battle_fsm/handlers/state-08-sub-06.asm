; main=8 sub=6: 电脑方行动桥接
; entry bank12 $BFB8; file $019FC8
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019FC8 b12:$BFB8 AC 8D 6F       LDY  $6F8D
019FCB b12:$BFBB 20 36 DC       JSR  $DC36 ; draw_officer_by_slot
019FCE b12:$BFBE AD 8C 6F       LDA  $6F8C
019FD1 b12:$BFC1 8D 09 05       STA  $0509
019FD4 b12:$BFC4 20 DE A1       JSR  $A1DE ; blink_menu_cursor
019FD7 b12:$BFC7 20 27 DF       JSR  $DF27 ; text_jobs_idle
019FDA b12:$BFCA 90 0F          BCC  $BFDB
019FDC b12:$BFCC 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
019FDF b12:$BFCF A5 81          LDA  $81
019FE1 b12:$BFD1 29 01          AND  #$01
019FE3 b12:$BFD3 F0 06          BEQ  $BFDB
019FE5 b12:$BFD5 EE 01 05       INC  $0501
019FE8 b12:$BFD8 20 EE EC       JSR  $ECEE ; wait_or_job_barrier
019FEB b12:$BFDB 60             RTS
