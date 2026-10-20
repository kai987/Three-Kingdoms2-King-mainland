; main=8 sub=15: 电脑方行动桥接
; entry bank13 $C1D1; file $01A1E1
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A1E1 b13:$C1D1 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A1E4 b13:$C1D4 90 14          BCC  $C1EA
01A1E6 b13:$C1D6 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01A1E9 b13:$C1D9 A5 81          LDA  $81
01A1EB b13:$C1DB 29 03          AND  #$03
01A1ED b13:$C1DD F0 0B          BEQ  $C1EA
01A1EF b13:$C1DF 20 F7 A1       JSR  $A1F7 ; reset_command_cursor
01A1F2 b13:$C1E2 A9 05          LDA  #$05
01A1F4 b13:$C1E4 20 93 F2       JSR  $F293 ; queue_message_job_0
01A1F7 b13:$C1E7 EE 01 05       INC  $0501
01A1FA b13:$C1EA 60             RTS
