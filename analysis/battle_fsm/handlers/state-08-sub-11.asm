; main=8 sub=11: 电脑方行动桥接
; entry bank13 $C110; file $01A120
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A120 b13:$C110 AC 8E 6F       LDY  $6F8E
01A123 b13:$C113 20 36 DC       JSR  $DC36 ; draw_officer_by_slot
01A126 b13:$C116 AD 8C 6F       LDA  $6F8C
01A129 b13:$C119 8D 09 05       STA  $0509
01A12C b13:$C11C 20 DE A1       JSR  $A1DE ; blink_menu_cursor
01A12F b13:$C11F 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A132 b13:$C122 90 16          BCC  $C13A
01A134 b13:$C124 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01A137 b13:$C127 A5 81          LDA  $81
01A139 b13:$C129 29 03          AND  #$03
01A13B b13:$C12B F0 0D          BEQ  $C13A
01A13D b13:$C12D 20 F7 A1       JSR  $A1F7 ; reset_command_cursor
01A140 b13:$C130 A9 05          LDA  #$05
01A142 b13:$C132 20 93 F2       JSR  $F293 ; queue_message_job_0
01A145 b13:$C135 A9 10          LDA  #$10
01A147 b13:$C137 8D 01 05       STA  $0501
01A14A b13:$C13A 60             RTS
