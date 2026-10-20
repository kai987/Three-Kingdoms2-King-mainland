; main=13 sub=5: 败方武将转移或转为在野
; entry bank13 $CE9E; file $01AEAE
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AD3A b13:$CD2A 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AD3D b13:$CD2D 20 E1 D0       JSR  $D0E1 ; select_next_postbattle_officer
01AD40 b13:$CD30 A9 FF          LDA  #$FF
01AD42 b13:$CD32 9D 2C 04       STA  $042C,X
01AD45 b13:$CD35 8A             TXA
01AD46 b13:$CD36 D0 0E          BNE  $CD46
01AD48 b13:$CD38 AD 0B 05       LDA  $050B
01AD4B b13:$CD3B 29 0F          AND  #$0F
01AD4D b13:$CD3D 8D 01 05       STA  $0501
01AD50 b13:$CD40 A9 0F          LDA  #$0F
01AD52 b13:$CD42 8D 00 05       STA  $0500
01AD55 b13:$CD45 60             RTS
01AD56 b13:$CD46 A9 DC          LDA  #$DC
01AD58 b13:$CD48 20 93 F2       JSR  $F293 ; queue_message_job_0
01AD5B b13:$CD4B 20 C3 D0       JSR  $D0C3 ; cpu_D0C3
01AD5E b13:$CD4E EE 01 05       INC  $0501
01AD61 b13:$CD51 60             RTS
01AEAE b13:$CE9E AD 0A 05       LDA  $050A
01AEB1 b13:$CEA1 0A             ASL  A
01AEB2 b13:$CEA2 A8             TAY
01AEB3 b13:$CEA3 B9 5E CF       LDA  $CF5E,Y
01AEB6 b13:$CEA6 85 10          STA  $10
01AEB8 b13:$CEA8 B9 5F CF       LDA  $CF5F,Y
01AEBB b13:$CEAB 85 11          STA  $11
01AEBD b13:$CEAD A9 00          LDA  #$00
01AEBF b13:$CEAF 85 12          STA  $12
01AEC1 b13:$CEB1 20 23 ED       JSR  $ED23 ; cpu_ED23
01AEC4 b13:$CEB4 A9 34          LDA  #$34
01AEC6 b13:$CEB6 85 10          STA  $10
01AEC8 b13:$CEB8 A9 CF          LDA  #$CF
01AECA b13:$CEBA 85 11          STA  $11
01AECC b13:$CEBC A9 04          LDA  #$04
01AECE b13:$CEBE 85 00          STA  $00
01AED0 b13:$CEC0 A9 CF          LDA  #$CF
01AED2 b13:$CEC2 85 01          STA  $01
01AED4 b13:$CEC4 A5 12          LDA  $12
01AED6 b13:$CEC6 8D 08 05       STA  $0508
01AED9 b13:$CEC9 20 F5 ED       JSR  $EDF5 ; cpu_EDF5
01AEDC b13:$CECC 20 67 D1       JSR  $D167 ; cpu_D167
01AEDF b13:$CECF 20 BC D1       JSR  $D1BC ; cpu_D1BC
01AEE2 b13:$CED2 A5 81          LDA  $81
01AEE4 b13:$CED4 29 01          AND  #$01
01AEE6 b13:$CED6 F0 2B          BEQ  $CF03
01AEE8 b13:$CED8 AD 0A 05       LDA  $050A
01AEEB b13:$CEDB CD 08 05       CMP  $0508
01AEEE b13:$CEDE D0 23          BNE  $CF03
01AEF0 b13:$CEE0 A0 00          LDY  #$00
01AEF2 b13:$CEE2 A2 00          LDX  #$00
01AEF4 b13:$CEE4 B9 80 05       LDA  $0580,Y
01AEF7 b13:$CEE7 30 01          BMI  $CEEA
01AEF9 b13:$CEE9 E8             INX
01AEFA b13:$CEEA C8             INY
01AEFB b13:$CEEB C0 14          CPY  #$14
01AEFD b13:$CEED 90 F5          BCC  $CEE4
01AEFF b13:$CEEF 8A             TXA
01AF00 b13:$CEF0 F0 28          BEQ  $CF1A
01AF02 b13:$CEF2 A9 D8          LDA  #$D8
01AF04 b13:$CEF4 AC 40 05       LDY  $0540
01AF07 b13:$CEF7 C0 1E          CPY  #$1E
01AF09 b13:$CEF9 D0 02          BNE  $CEFD
01AF0B b13:$CEFB A9 E6          LDA  #$E6
01AF0D b13:$CEFD 20 83 F2       JSR  $F283 ; queue_message_job_1
01AF10 b13:$CF00 EE 01 05       INC  $0501
01AF13 b13:$CF03 60             RTS
01AF2A b13:$CF1A A9 E1          LDA  #$E1
01AF2C b13:$CF1C 85 E6          STA  $E6
01AF2E b13:$CF1E 85 E7          STA  $E7
01AF30 b13:$CF20 A9 00          LDA  #$00
01AF32 b13:$CF22 85 8E          STA  $8E
01AF34 b13:$CF24 A9 50          LDA  #$50
01AF36 b13:$CF26 85 90          STA  $90
01AF38 b13:$CF28 A9 00          LDA  #$00
01AF3A b13:$CF2A 8D 01 05       STA  $0501
01AF3D b13:$CF2D 20 F9 D1       JSR  $D1F9 ; cpu_D1F9
01AF40 b13:$CF30 4C 2A CD       JMP  $CD2A
