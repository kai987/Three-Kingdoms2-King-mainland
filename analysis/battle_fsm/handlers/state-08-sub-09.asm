; main=8 sub=9: 电脑方行动桥接
; entry bank13 $C054; file $01A064
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A064 b13:$C054 EE 2D 04       INC  $042D
01A067 b13:$C057 A9 00          LDA  #$00
01A069 b13:$C059 8D A4 00       STA  $00A4
01A06C b13:$C05C AC 8E 6F       LDY  $6F8E
01A06F b13:$C05F 20 36 DC       JSR  $DC36 ; draw_officer_by_slot
01A072 b13:$C062 AD 8C 6F       LDA  $6F8C
01A075 b13:$C065 8D 09 05       STA  $0509
01A078 b13:$C068 20 DE A1       JSR  $A1DE ; blink_menu_cursor
01A07B b13:$C06B 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A07E b13:$C06E 90 0C          BCC  $C07C
01A080 b13:$C070 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01A083 b13:$C073 A5 81          LDA  $81
01A085 b13:$C075 29 03          AND  #$03
01A087 b13:$C077 F0 03          BEQ  $C07C
01A089 b13:$C079 EE 01 05       INC  $0501
01A08C b13:$C07C 60             RTS
