; release_all_without_destination: No-space outcome: leader status3, others status0/current city
; Source semantics are direct Python; this is exact ROM provenance.
01AD48 b13:$CD38 AD 0B 05       LDA  $050B
01AD4B b13:$CD3B 29 0F          AND  #$0F
01AD4D b13:$CD3D 8D 01 05       STA  $0501
01AD50 b13:$CD40 A9 0F          LDA  #$0F
01AD52 b13:$CD42 8D 00 05       STA  $0500
01AD55 b13:$CD45 60             RTS
01ADAC b13:$CD9C AD 07 05       LDA  $0507
01ADAF b13:$CD9F AC 0B 05       LDY  $050B
01ADB2 b13:$CDA2 C0 02          CPY  #$02
01ADB4 b13:$CDA4 F0 04          BEQ  $CDAA
01ADB6 b13:$CDA6 4A             LSR  A
01ADB7 b13:$CDA7 4A             LSR  A
01ADB8 b13:$CDA8 4A             LSR  A
01ADB9 b13:$CDA9 4A             LSR  A
01ADBA b13:$CDAA 29 0F          AND  #$0F
01ADBC b13:$CDAC 20 68 F3       JSR  $F368
01ADBF b13:$CDAF A0 00          LDY  #$00
01ADC1 b13:$CDB1 B1 00          LDA  ($00),Y
01ADC3 b13:$CDB3 85 03          STA  $03
01ADC5 b13:$CDB5 20 E1 D0       JSR  $D0E1
01ADC8 b13:$CDB8 A2 00          LDX  #$00
01ADCA b13:$CDBA BD 2C 04       LDA  $042C,X
01ADCD b13:$CDBD C9 FE          CMP  #$FE
01ADCF b13:$CDBF B0 1A          BCS  $CDDB
01ADD1 b13:$CDC1 C5 03          CMP  $03
01ADD3 b13:$CDC3 F0 1E          BEQ  $CDE3
01ADD5 b13:$CDC5 20 D7 F2       JSR  $F2D7
01ADD8 b13:$CDC8 A0 0B          LDY  #$0B
01ADDA b13:$CDCA B1 00          LDA  ($00),Y
01ADDC b13:$CDCC 29 FC          AND  #$FC
01ADDE b13:$CDCE 91 00          STA  ($00),Y
01ADE0 b13:$CDD0 A0 05          LDY  #$05
01ADE2 b13:$CDD2 AD 0E 05       LDA  $050E
01ADE5 b13:$CDD5 91 00          STA  ($00),Y
01ADE7 b13:$CDD7 E8             INX
01ADE8 b13:$CDD8 4C BA CD       JMP  $CDBA
01ADEB b13:$CDDB A9 00          LDA  #$00
01ADED b13:$CDDD 8D 01 05       STA  $0501
01ADF0 b13:$CDE0 4C 38 CD       JMP  $CD38
01ADF3 b13:$CDE3 20 D7 F2       JSR  $F2D7
01ADF6 b13:$CDE6 A0 0B          LDY  #$0B
01ADF8 b13:$CDE8 B1 00          LDA  ($00),Y
01ADFA b13:$CDEA 09 03          ORA  #$03
01ADFC b13:$CDEC 91 00          STA  ($00),Y
01ADFE b13:$CDEE E8             INX
01ADFF b13:$CDEF 4C BA CD       JMP  $CDBA
