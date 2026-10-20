; bank31 $EBE9, file $03EBF9
; u24 $00..02 times u8 $03; full product06..09; inputs/scratch mutated
03EBF9 b31:$EBE9 A0 07          LDY  #$07
03EBFB b31:$EBEB A9 00          LDA  #$00
03EBFD b31:$EBED 85 04          STA  $04
03EBFF b31:$EBEF 85 05          STA  $05
03EC01 b31:$EBF1 85 06          STA  $06
03EC03 b31:$EBF3 85 07          STA  $07
03EC05 b31:$EBF5 85 08          STA  $08
03EC07 b31:$EBF7 85 09          STA  $09
03EC09 b31:$EBF9 46 03          LSR  $03
03EC0B b31:$EBFB 90 19          BCC  $EC16
03EC0D b31:$EBFD A5 00          LDA  $00
03EC0F b31:$EBFF 18             CLC
03EC10 b31:$EC00 65 06          ADC  $06
03EC12 b31:$EC02 85 06          STA  $06
03EC14 b31:$EC04 A5 01          LDA  $01
03EC16 b31:$EC06 65 07          ADC  $07
03EC18 b31:$EC08 85 07          STA  $07
03EC1A b31:$EC0A A5 02          LDA  $02
03EC1C b31:$EC0C 65 08          ADC  $08
03EC1E b31:$EC0E 85 08          STA  $08
03EC20 b31:$EC10 A5 04          LDA  $04
03EC22 b31:$EC12 65 09          ADC  $09
03EC24 b31:$EC14 85 09          STA  $09
03EC26 b31:$EC16 06 00          ASL  $00
03EC28 b31:$EC18 26 01          ROL  $01
03EC2A b31:$EC1A 26 02          ROL  $02
03EC2C b31:$EC1C 26 04          ROL  $04
03EC2E b31:$EC1E 88             DEY
03EC2F b31:$EC1F 10 D8          BPL  $EBF9
03EC31 b31:$EC21 60             RTS
