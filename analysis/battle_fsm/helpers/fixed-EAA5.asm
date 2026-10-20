; bank31 $EAA5, file $03EAB5
; u24 $00..02 / u16 $03..04; quotient00..02, remainder05..07
03EAB5 b31:$EAA5 A9 00          LDA  #$00
03EAB7 b31:$EAA7 85 05          STA  $05
03EAB9 b31:$EAA9 85 06          STA  $06
03EABB b31:$EAAB 85 07          STA  $07
03EABD b31:$EAAD A0 17          LDY  #$17
03EABF b31:$EAAF 06 00          ASL  $00
03EAC1 b31:$EAB1 26 01          ROL  $01
03EAC3 b31:$EAB3 26 02          ROL  $02
03EAC5 b31:$EAB5 26 05          ROL  $05
03EAC7 b31:$EAB7 26 06          ROL  $06
03EAC9 b31:$EAB9 26 07          ROL  $07
03EACB b31:$EABB A5 05          LDA  $05
03EACD b31:$EABD 38             SEC
03EACE b31:$EABE E5 03          SBC  $03
03EAD0 b31:$EAC0 85 08          STA  $08
03EAD2 b31:$EAC2 A5 06          LDA  $06
03EAD4 b31:$EAC4 E5 04          SBC  $04
03EAD6 b31:$EAC6 85 09          STA  $09
03EAD8 b31:$EAC8 A5 07          LDA  $07
03EADA b31:$EACA E9 00          SBC  #$00
03EADC b31:$EACC 90 0C          BCC  $EADA
03EADE b31:$EACE 85 07          STA  $07
03EAE0 b31:$EAD0 A5 08          LDA  $08
03EAE2 b31:$EAD2 85 05          STA  $05
03EAE4 b31:$EAD4 A5 09          LDA  $09
03EAE6 b31:$EAD6 85 06          STA  $06
03EAE8 b31:$EAD8 E6 00          INC  $00
03EAEA b31:$EADA 88             DEY
03EAEB b31:$EADB 10 D2          BPL  $EAAF
03EAED b31:$EADD 60             RTS
