; bank31 $EA7C, file $03EA8C
; u16 $01..02 / u16 $03..04; quotient01..02, remainder05..06
03EA8C b31:$EA7C A9 00          LDA  #$00
03EA8E b31:$EA7E 85 05          STA  $05
03EA90 b31:$EA80 85 06          STA  $06
03EA92 b31:$EA82 A0 0F          LDY  #$0F
03EA94 b31:$EA84 06 01          ASL  $01
03EA96 b31:$EA86 26 02          ROL  $02
03EA98 b31:$EA88 26 05          ROL  $05
03EA9A b31:$EA8A 26 06          ROL  $06
03EA9C b31:$EA8C A5 05          LDA  $05
03EA9E b31:$EA8E 38             SEC
03EA9F b31:$EA8F E5 03          SBC  $03
03EAA1 b31:$EA91 85 07          STA  $07
03EAA3 b31:$EA93 A5 06          LDA  $06
03EAA5 b31:$EA95 E5 04          SBC  $04
03EAA7 b31:$EA97 90 08          BCC  $EAA1
03EAA9 b31:$EA99 85 06          STA  $06
03EAAB b31:$EA9B A5 07          LDA  $07
03EAAD b31:$EA9D 85 05          STA  $05
03EAAF b31:$EA9F E6 01          INC  $01
03EAB1 b31:$EAA1 88             DEY
03EAB2 b31:$EAA2 10 E0          BPL  $EA84
03EAB4 b31:$EAA4 60             RTS
