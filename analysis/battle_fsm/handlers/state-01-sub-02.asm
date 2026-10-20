; main=1 sub=2: 单位信息
; entry bank12 $A27B; file $01828B
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01828B b12:$A27B 20 DE A1       JSR  $A1DE ; blink_menu_cursor
01828E b12:$A27E 20 27 DF       JSR  $DF27 ; text_jobs_idle
018291 b12:$A281 90 0F          BCC  $A292
018293 b12:$A283 A9 09          LDA  #$09
018295 b12:$A285 85 BB          STA  $BB
018297 b12:$A287 A9 00          LDA  #$00
018299 b12:$A289 8D 00 05       STA  $0500
01829C b12:$A28C 8D 01 05       STA  $0501
01829F b12:$A28F 20 F7 A1       JSR  $A1F7 ; reset_command_cursor
0182A2 b12:$A292 60             RTS
