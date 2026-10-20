; main=8 sub=14: 电脑方行动桥接
; entry bank13 $C178; file $01A188
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A14A b13:$C13A 60             RTS
01A188 b13:$C178 A9 00          LDA  #$00
01A18A b13:$C17A 8D A4 00       STA  $00A4
01A18D b13:$C17D AC 0A 05       LDY  $050A
01A190 b13:$C180 20 36 DC       JSR  $DC36 ; draw_officer_by_slot
01A193 b13:$C183 20 DE A1       JSR  $A1DE ; blink_menu_cursor
01A196 b13:$C186 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A199 b13:$C189 90 AF          BCC  $C13A
01A19B b13:$C18B 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01A19E b13:$C18E A5 81          LDA  $81
01A1A0 b13:$C190 29 03          AND  #$03
01A1A2 b13:$C192 F0 1A          BEQ  $C1AE
01A1A4 b13:$C194 A9 00          LDA  #$00
01A1A6 b13:$C196 85 12          STA  $12
01A1A8 b13:$C198 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
01A1AB b13:$C19B AD 8D 6F       LDA  $6F8D
01A1AE b13:$C19E 8D 0B 05       STA  $050B
01A1B1 b13:$C1A1 20 2A BC       JSR  $BC2A ; cpu_BC2A
01A1B4 b13:$C1A4 A9 05          LDA  #$05
01A1B6 b13:$C1A6 20 93 F2       JSR  $F293 ; queue_message_job_0
01A1B9 b13:$C1A9 A9 10          LDA  #$10
01A1BB b13:$C1AB 8D 01 05       STA  $0501
01A1BE b13:$C1AE 60             RTS
