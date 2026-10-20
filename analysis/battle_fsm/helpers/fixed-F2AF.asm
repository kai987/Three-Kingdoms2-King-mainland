; bank31 $F2AF, file $03F2BF
; City pointer $6000 +32*A -> $00..01; exact registers/flags retained by IR
03F2BF b31:$F2AF A0 00          LDY  #$00
03F2C1 b31:$F2B1 8C 01 00       STY  $0001
03F2C4 b31:$F2B4 0A             ASL  A
03F2C5 b31:$F2B5 2E 01 00       ROL  $0001
03F2C8 b31:$F2B8 0A             ASL  A
03F2C9 b31:$F2B9 2E 01 00       ROL  $0001
03F2CC b31:$F2BC 0A             ASL  A
03F2CD b31:$F2BD 2E 01 00       ROL  $0001
03F2D0 b31:$F2C0 0A             ASL  A
03F2D1 b31:$F2C1 2E 01 00       ROL  $0001
03F2D4 b31:$F2C4 0A             ASL  A
03F2D5 b31:$F2C5 2E 01 00       ROL  $0001
03F2D8 b31:$F2C8 18             CLC
03F2D9 b31:$F2C9 69 00          ADC  #$00
03F2DB b31:$F2CB 8D 00 00       STA  $0000
03F2DE b31:$F2CE AD 01 00       LDA  $0001
03F2E1 b31:$F2D1 69 60          ADC  #$60
03F2E3 b31:$F2D3 8D 01 00       STA  $0001
03F2E6 b31:$F2D6 60             RTS
