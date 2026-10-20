; main=10 sub=6: 下一方回合准备
; entry bank13 $C350; file $01A360
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A360 b13:$C350 A9 A7          LDA  #$A7
01A362 b13:$C352 85 0A          STA  $0A
01A364 b13:$C354 AD 10 04       LDA  $0410
01A367 b13:$C357 85 00          STA  $00
01A369 b13:$C359 A9 00          LDA  #$00
01A36B b13:$C35B 8D A4 00       STA  $00A4
01A36E b13:$C35E A0 39          LDY  #$39
01A370 b13:$C360 20 07 EE       JSR  $EE07 ; far_A000
; inline .word $A000, resumes $C365
01A375 b13:$C365 AC 09 05       LDY  $0509
01A378 b13:$C368 B9 00 06       LDA  $0600,Y
01A37B b13:$C36B 85 00          STA  $00
01A37D b13:$C36D B9 14 06       LDA  $0614,Y
01A380 b13:$C370 85 02          STA  $02
01A382 b13:$C372 20 5A DA       JSR  $DA5A ; tile_to_pixel_coordinates
01A385 b13:$C375 A5 00          LDA  $00
01A387 b13:$C377 8D 3F 6F       STA  $6F3F
01A38A b13:$C37A A5 01          LDA  $01
01A38C b13:$C37C 8D 40 6F       STA  $6F40
01A38F b13:$C37F A5 02          LDA  $02
01A391 b13:$C381 8D 41 6F       STA  $6F41
01A394 b13:$C384 A5 03          LDA  $03
01A396 b13:$C386 8D 42 6F       STA  $6F42
01A399 b13:$C389 20 EE D5       JSR  $D5EE ; battle_cursor_input
01A39C b13:$C38C AD 08 05       LDA  $0508
01A39F b13:$C38F D0 39          BNE  $C3CA
01A3A1 b13:$C391 AD 7E 00       LDA  $007E
01A3A4 b13:$C394 D0 34          BNE  $C3CA
01A3A6 b13:$C396 A9 06          LDA  #$06
01A3A8 b13:$C398 85 BB          STA  $BB
01A3AA b13:$C39A A0 39          LDY  #$39
01A3AC b13:$C39C 20 07 EE       JSR  $EE07 ; far_A012
; inline .word $A012, resumes $C3A1
01A3B1 b13:$C3A1 20 DE A1       JSR  $A1DE ; blink_menu_cursor
01A3B4 b13:$C3A4 AD 0D 04       LDA  $040D
01A3B7 b13:$C3A7 C9 FF          CMP  #$FF
01A3B9 b13:$C3A9 D0 1F          BNE  $C3CA
01A3BB b13:$C3AB 20 B1 C4       JSR  $C4B1 ; cpu_C4B1
01A3BE b13:$C3AE 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A3C1 b13:$C3B1 90 17          BCC  $C3CA
01A3C3 b13:$C3B3 A5 81          LDA  $81
01A3C5 b13:$C3B5 C9 10          CMP  #$10
01A3C7 b13:$C3B7 B0 11          BCS  $C3CA
01A3C9 b13:$C3B9 29 01          AND  #$01
01A3CB b13:$C3BB F0 0D          BEQ  $C3CA
01A3CD b13:$C3BD CE 01 05       DEC  $0501
01A3D0 b13:$C3C0 A9 01          LDA  #$01
01A3D2 b13:$C3C2 85 12          STA  $12
01A3D4 b13:$C3C4 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
01A3D7 b13:$C3C7 EE 09 05       INC  $0509
01A3DA b13:$C3CA 60             RTS
