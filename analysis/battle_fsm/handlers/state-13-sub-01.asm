; main=13 sub=1: 败方武将转移或转为在野
; entry bank13 $CD52; file $01AD62
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AD48 b13:$CD38 AD 0B 05       LDA  $050B
01AD4B b13:$CD3B 29 0F          AND  #$0F
01AD4D b13:$CD3D 8D 01 05       STA  $0501
01AD50 b13:$CD40 A9 0F          LDA  #$0F
01AD52 b13:$CD42 8D 00 05       STA  $0500
01AD55 b13:$CD45 60             RTS
01AD62 b13:$CD52 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AD65 b13:$CD55 20 27 DF       JSR  $DF27 ; text_jobs_idle
01AD68 b13:$CD58 90 09          BCC  $CD63
01AD6A b13:$CD5A 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01AD6D b13:$CD5D A5 81          LDA  $81
01AD6F b13:$CD5F 29 01          AND  #$01
01AD71 b13:$CD61 D0 01          BNE  $CD64
01AD73 b13:$CD63 60             RTS
01AD74 b13:$CD64 EE 01 05       INC  $0501
01AD77 b13:$CD67 A9 00          LDA  #$00
01AD79 b13:$CD69 8D 24 04       STA  $0424
01AD7C b13:$CD6C 8D 25 04       STA  $0425
01AD7F b13:$CD6F AD 0B 05       LDA  $050B
01AD82 b13:$CD72 29 10          AND  #$10
01AD84 b13:$CD74 0A             ASL  A
01AD85 b13:$CD75 0A             ASL  A
01AD86 b13:$CD76 0A             ASL  A
01AD87 b13:$CD77 8D 04 05       STA  $0504
01AD8A b13:$CD7A 20 84 BB       JSR  $BB84 ; cpu_BB84
01AD8D b13:$CD7D EE 0A 05       INC  $050A
01AD90 b13:$CD80 AD 0A 05       LDA  $050A
01AD93 b13:$CD83 F0 17          BEQ  $CD9C
01AD95 b13:$CD85 A8             TAY
01AD96 b13:$CD86 A9 1E          LDA  #$1E
01AD98 b13:$CD88 99 2C 04       STA  $042C,Y
01AD9B b13:$CD8B 88             DEY
01AD9C b13:$CD8C B9 50 05       LDA  $0550,Y
01AD9F b13:$CD8F C9 0A          CMP  #$0A
01ADA1 b13:$CD91 B0 06          BCS  $CD99
01ADA3 b13:$CD93 A9 D7          LDA  #$D7
01ADA5 b13:$CD95 20 83 F2       JSR  $F283 ; queue_message_job_1
01ADA8 b13:$CD98 60             RTS
01ADA9 b13:$CD99 88             DEY
01ADAA b13:$CD9A 10 F0          BPL  $CD8C
01ADAC b13:$CD9C AD 07 05       LDA  $0507
01ADAF b13:$CD9F AC 0B 05       LDY  $050B
01ADB2 b13:$CDA2 C0 02          CPY  #$02
01ADB4 b13:$CDA4 F0 04          BEQ  $CDAA
01ADB6 b13:$CDA6 4A             LSR  A
01ADB7 b13:$CDA7 4A             LSR  A
01ADB8 b13:$CDA8 4A             LSR  A
01ADB9 b13:$CDA9 4A             LSR  A
01ADBA b13:$CDAA 29 0F          AND  #$0F
01ADBC b13:$CDAC 20 68 F3       JSR  $F368 ; ruler_record_pointer
01ADBF b13:$CDAF A0 00          LDY  #$00
01ADC1 b13:$CDB1 B1 00          LDA  ($00),Y
01ADC3 b13:$CDB3 85 03          STA  $03
01ADC5 b13:$CDB5 20 E1 D0       JSR  $D0E1 ; select_next_postbattle_officer
01ADC8 b13:$CDB8 A2 00          LDX  #$00
01ADCA b13:$CDBA BD 2C 04       LDA  $042C,X
01ADCD b13:$CDBD C9 FE          CMP  #$FE
01ADCF b13:$CDBF B0 1A          BCS  $CDDB
01ADD1 b13:$CDC1 C5 03          CMP  $03
01ADD3 b13:$CDC3 F0 1E          BEQ  $CDE3
01ADD5 b13:$CDC5 20 D7 F2       JSR  $F2D7 ; officer_record_pointer
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
01ADF3 b13:$CDE3 20 D7 F2       JSR  $F2D7 ; officer_record_pointer
01ADF6 b13:$CDE6 A0 0B          LDY  #$0B
01ADF8 b13:$CDE8 B1 00          LDA  ($00),Y
01ADFA b13:$CDEA 09 03          ORA  #$03
01ADFC b13:$CDEC 91 00          STA  ($00),Y
01ADFE b13:$CDEE E8             INX
01ADFF b13:$CDEF 4C BA CD       JMP  $CDBA
