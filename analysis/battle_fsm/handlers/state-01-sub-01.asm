; main=1 sub=1: 单位信息
; entry bank12 $A244; file $018254
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018254 b12:$A244 20 DE A1       JSR  $A1DE ; blink_menu_cursor
018257 b12:$A247 A9 A7          LDA  #$A7
018259 b12:$A249 85 0A          STA  $0A
01825B b12:$A24B AD 10 04       LDA  $0410
01825E b12:$A24E 85 00          STA  $00
018260 b12:$A250 A9 00          LDA  #$00
018262 b12:$A252 8D A4 00       STA  $00A4
018265 b12:$A255 A0 39          LDY  #$39
018267 b12:$A257 20 07 EE       JSR  $EE07 ; far_A000
; inline .word $A000, resumes $A25C
01826C b12:$A25C A9 06          LDA  #$06
01826E b12:$A25E 85 BB          STA  $BB
018270 b12:$A260 A0 39          LDY  #$39
018272 b12:$A262 20 07 EE       JSR  $EE07 ; far_A012
; inline .word $A012, resumes $A267
018277 b12:$A267 20 27 DF       JSR  $DF27 ; text_jobs_idle
01827A b12:$A26A 90 0E          BCC  $A27A
01827C b12:$A26C A5 81          LDA  $81
01827E b12:$A26E 29 03          AND  #$03
018280 b12:$A270 F0 08          BEQ  $A27A
018282 b12:$A272 EE 01 05       INC  $0501
018285 b12:$A275 A9 05          LDA  #$05
018287 b12:$A277 20 93 F2       JSR  $F293 ; queue_message_job_0
01828A b12:$A27A 60             RTS
