; main=0 sub=4: 单位选择与行动菜单
; entry bank12 $A1B8; file $0181C8
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0181C8 b12:$A1B8 A9 00          LDA  #$00
0181CA b12:$A1BA 8D A4 00       STA  $00A4
0181CD b12:$A1BD 20 33 DC       JSR  $DC33 ; draw_active_unit
0181D0 b12:$A1C0 20 DE A1       JSR  $A1DE ; blink_menu_cursor
0181D3 b12:$A1C3 20 27 DF       JSR  $DF27 ; text_jobs_idle
0181D6 b12:$A1C6 90 15          BCC  $A1DD
0181D8 b12:$A1C8 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
0181DB b12:$A1CB A5 81          LDA  $81
0181DD b12:$A1CD 29 03          AND  #$03
0181DF b12:$A1CF F0 0C          BEQ  $A1DD
0181E1 b12:$A1D1 A9 01          LDA  #$01
0181E3 b12:$A1D3 8D 01 05       STA  $0501
0181E6 b12:$A1D6 A9 01          LDA  #$01
0181E8 b12:$A1D8 85 12          STA  $12
0181EA b12:$A1DA 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
0181ED b12:$A1DD 60             RTS
