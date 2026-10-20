; main=4 sub=1: 移动
; entry bank12 $A47E; file $01848E
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01848E b12:$A47E 20 DE A1       JSR  $A1DE ; blink_menu_cursor
018491 b12:$A481 20 4A A6       JSR  $A64A ; cpu_A64A
018494 b12:$A484 AC 09 05       LDY  $0509
018497 b12:$A487 B9 00 06       LDA  $0600,Y
01849A b12:$A48A 85 00          STA  $00
01849C b12:$A48C B9 14 06       LDA  $0614,Y
01849F b12:$A48F 85 02          STA  $02
0184A1 b12:$A491 20 5A DA       JSR  $DA5A ; tile_to_pixel_coordinates
0184A4 b12:$A494 A5 00          LDA  $00
0184A6 b12:$A496 8D 3F 6F       STA  $6F3F
0184A9 b12:$A499 A5 01          LDA  $01
0184AB b12:$A49B 8D 40 6F       STA  $6F40
0184AE b12:$A49E A5 02          LDA  $02
0184B0 b12:$A4A0 8D 41 6F       STA  $6F41
0184B3 b12:$A4A3 A5 03          LDA  $03
0184B5 b12:$A4A5 8D 42 6F       STA  $6F42
0184B8 b12:$A4A8 20 EE D5       JSR  $D5EE ; battle_cursor_input
0184BB b12:$A4AB A5 81          LDA  $81
0184BD b12:$A4AD 29 01          AND  #$01
0184BF b12:$A4AF F0 03          BEQ  $A4B4
0184C1 b12:$A4B1 EE 01 05       INC  $0501
0184C4 b12:$A4B4 60             RTS
