; human_neighbor_cities: Original destination menu and occupancy scratch
; Source semantics are direct Python; this is exact ROM provenance.
019B94 b12:$BB84 A9 FF          LDA  #$FF
019B96 b12:$BB86 8D 0A 05       STA  $050A
019B99 b12:$BB89 A0 3F          LDY  #$3F
019B9B b12:$BB8B A9 FF          LDA  #$FF
019B9D b12:$BB8D 99 2C 04       STA  $042C,Y
019BA0 b12:$BB90 88             DEY
019BA1 b12:$BB91 10 FA          BPL  $BB8D
019BA3 b12:$BB93 A0 0F          LDY  #$0F
019BA5 b12:$BB95 A9 FF          LDA  #$FF
019BA7 b12:$BB97 99 50 05       STA  $0550,Y
019BAA b12:$BB9A 88             DEY
019BAB b12:$BB9B 10 FA          BPL  $BB97
019BAD b12:$BB9D AD 07 05       LDA  $0507
019BB0 b12:$BBA0 AC 04 05       LDY  $0504
019BB3 b12:$BBA3 10 04          BPL  $BBA9
019BB5 b12:$BBA5 4A             LSR  A
019BB6 b12:$BBA6 4A             LSR  A
019BB7 b12:$BBA7 4A             LSR  A
019BB8 b12:$BBA8 4A             LSR  A
019BB9 b12:$BBA9 29 0F          AND  #$0F
019BBB b12:$BBAB 85 02          STA  $02
019BBD b12:$BBAD A0 30          LDY  #$30
019BBF b12:$BBAF 20 5F F2       JSR  $F25F
019BC2 b12:$BBB2 AD 0E 05       LDA  $050E
019BC5 b12:$BBB5 0A             ASL  A
019BC6 b12:$BBB6 0A             ASL  A
019BC7 b12:$BBB7 0A             ASL  A
019BC8 b12:$BBB8 A8             TAY
019BC9 b12:$BBB9 A2 00          LDX  #$00
019BCB b12:$BBBB B9 72 9D       LDA  $9D72,Y
019BCE b12:$BBBE 30 48          BMI  $BC08
019BD0 b12:$BBC0 85 03          STA  $03
019BD2 b12:$BBC2 84 04          STY  $04
019BD4 b12:$BBC4 20 AF F2       JSR  $F2AF
019BD7 b12:$BBC7 A0 00          LDY  #$00
019BD9 b12:$BBC9 B1 00          LDA  ($00),Y
019BDB b12:$BBCB 29 07          AND  #$07
019BDD b12:$BBCD C9 07          CMP  #$07
019BDF b12:$BBCF F0 04          BEQ  $BBD5
019BE1 b12:$BBD1 C5 02          CMP  $02
019BE3 b12:$BBD3 D0 2B          BNE  $BC00
019BE5 b12:$BBD5 8A             TXA
019BE6 b12:$BBD6 48             PHA
019BE7 b12:$BBD7 EE 0A 05       INC  $050A
019BEA b12:$BBDA AC 0A 05       LDY  $050A
019BED b12:$BBDD A5 03          LDA  $03
019BEF b12:$BBDF 99 2C 04       STA  $042C,Y
019BF2 b12:$BBE2 20 14 BC       JSR  $BC14
019BF5 b12:$BBE5 AC 0A 05       LDY  $050A
019BF8 b12:$BBE8 B9 09 BC       LDA  $BC09,Y
019BFB b12:$BBEB A8             TAY
019BFC b12:$BBEC A9 00          LDA  #$00
019BFE b12:$BBEE 99 2D 04       STA  $042D,Y
019C01 b12:$BBF1 99 2E 04       STA  $042E,Y
019C04 b12:$BBF4 8A             TXA
019C05 b12:$BBF5 99 2C 04       STA  $042C,Y
019C08 b12:$BBF8 AC 0A 05       LDY  $050A
019C0B b12:$BBFB 99 50 05       STA  $0550,Y
019C0E b12:$BBFE 68             PLA
019C0F b12:$BBFF AA             TAX
019C10 b12:$BC00 A4 04          LDY  $04
019C12 b12:$BC02 C8             INY
019C13 b12:$BC03 E8             INX
019C14 b12:$BC04 E0 08          CPX  #$08
019C16 b12:$BC06 90 B3          BCC  $BBBB
019C18 b12:$BC08 60             RTS
