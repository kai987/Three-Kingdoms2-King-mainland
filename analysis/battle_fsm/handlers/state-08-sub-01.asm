; main=8 sub=1: 电脑方行动桥接
; entry bank12 $BEBA; file $019ECA
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019ECA b12:$BEBA AD 8B 6F       LDA  $6F8B
019ECD b12:$BEBD C9 FF          CMP  #$FF
019ECF b12:$BEBF D0 3F          BNE  $BF00
019ED1 b12:$BEC1 AD 8F 6F       LDA  $6F8F
019ED4 b12:$BEC4 C9 03          CMP  #$03
019ED6 b12:$BEC6 F0 35          BEQ  $BEFD
019ED8 b12:$BEC8 AD 8C 6F       LDA  $6F8C
019EDB b12:$BECB 8D 09 05       STA  $0509
019EDE b12:$BECE A8             TAY
019EDF b12:$BECF B9 00 06       LDA  $0600,Y
019EE2 b12:$BED2 85 00          STA  $00
019EE4 b12:$BED4 B9 14 06       LDA  $0614,Y
019EE7 b12:$BED7 85 02          STA  $02
019EE9 b12:$BED9 20 5A DA       JSR  $DA5A ; tile_to_pixel_coordinates
019EEC b12:$BEDC A5 00          LDA  $00
019EEE b12:$BEDE 8D 3F 6F       STA  $6F3F
019EF1 b12:$BEE1 A5 01          LDA  $01
019EF3 b12:$BEE3 8D 40 6F       STA  $6F40
019EF6 b12:$BEE6 A5 02          LDA  $02
019EF8 b12:$BEE8 8D 41 6F       STA  $6F41
019EFB b12:$BEEB A5 03          LDA  $03
019EFD b12:$BEED 8D 42 6F       STA  $6F42
019F00 b12:$BEF0 20 EE D5       JSR  $D5EE ; battle_cursor_input
019F03 b12:$BEF3 AD 08 05       LDA  $0508
019F06 b12:$BEF6 D0 08          BNE  $BF00
019F08 b12:$BEF8 AD 7E 00       LDA  $007E
019F0B b12:$BEFB D0 03          BNE  $BF00
019F0D b12:$BEFD EE 01 05       INC  $0501
019F10 b12:$BF00 60             RTS
