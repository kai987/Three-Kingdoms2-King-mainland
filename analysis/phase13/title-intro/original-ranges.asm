; title_intro_code_23_A021: physical23 $A021..$A023, file0x02E031, code
02E031  b23:$A021  4C 25 DE  JMP  $DE25

; title_intro_code_24_DE25: physical24 $DE25..$DE39, file0x031E35, code
031E35  b24:$DE25  AD 81 00  LDA  $0081
031E38  b24:$DE28  29 08     AND  #$08
031E3A  b24:$DE2A  F0 08     BEQ  $DE34
031E3C  b24:$DE2C  A9 03     LDA  #$03
031E3E  b24:$DE2E  8D 41 05  STA  $0541
031E41  b24:$DE31  4C C7 DE  JMP  $DEC7
031E44  b24:$DE34  AD 41 05  LDA  $0541
031E47  b24:$DE37  20 DE EA  JSR  $EADE

; title_intro_code_24_DE44: physical24 $DE44..$DE9F, file0x031E54, code
031E54  b24:$DE44  EE 44 05  INC  $0544
031E57  b24:$DE47  AD 44 05  LDA  $0544
031E5A  b24:$DE4A  C9 20     CMP  #$20
031E5C  b24:$DE4C  90 17     BCC  $DE65
031E5E  b24:$DE4E  A9 16     LDA  #$16
031E60  b24:$DE50  8D 15 01  STA  $0115
031E63  b24:$DE53  A9 30     LDA  #$30
031E65  b24:$DE55  8D 16 01  STA  $0116
031E68  b24:$DE58  A9 00     LDA  #$00
031E6A  b24:$DE5A  8D 43 05  STA  $0543
031E6D  b24:$DE5D  A9 02     LDA  #$02
031E6F  b24:$DE5F  8D 44 05  STA  $0544
031E72  b24:$DE62  EE 41 05  INC  $0541
031E75  b24:$DE65  60        RTS
031E76  b24:$DE66  AC 43 05  LDY  $0543
031E79  b24:$DE69  C0 14     CPY  #$14
031E7B  b24:$DE6B  D0 05     BNE  $DE72
031E7D  b24:$DE6D  A9 62     LDA  #$62
031E7F  b24:$DE6F  20 93 E6  JSR  $E693
031E82  b24:$DE72  A0 21     LDY  #$21
031E84  b24:$DE74  20 5F F2  JSR  $F25F
031E87  b24:$DE77  AC 43 05  LDY  $0543
031E8A  b24:$DE7A  B9 A0 DE  LDA  $DEA0,Y
031E8D  b24:$DE7D  20 FA DE  JSR  $DEFA
031E90  b24:$DE80  CE 44 05  DEC  $0544
031E93  b24:$DE83  D0 1A     BNE  $DE9F
031E95  b24:$DE85  A9 02     LDA  #$02
031E97  b24:$DE87  8D 44 05  STA  $0544
031E9A  b24:$DE8A  EE 43 05  INC  $0543
031E9D  b24:$DE8D  AC 43 05  LDY  $0543
031EA0  b24:$DE90  B9 A0 DE  LDA  $DEA0,Y
031EA3  b24:$DE93  C9 FF     CMP  #$FF
031EA5  b24:$DE95  D0 08     BNE  $DE9F
031EA7  b24:$DE97  EE 41 05  INC  $0541
031EAA  b24:$DE9A  A9 40     LDA  #$40
031EAC  b24:$DE9C  8D 44 05  STA  $0544
031EAF  b24:$DE9F  60        RTS

; title_intro_code_24_DEB9: physical24 $DEB9..$DF14, file0x031EC9, code
031EC9  b24:$DEB9  CE 44 05  DEC  $0544
031ECC  b24:$DEBC  F0 05     BEQ  $DEC3
031ECE  b24:$DEBE  A9 08     LDA  #$08
031ED0  b24:$DEC0  4C FA DE  JMP  $DEFA
031ED3  b24:$DEC3  EE 41 05  INC  $0541
031ED6  b24:$DEC6  60        RTS
031ED7  b24:$DEC7  EE 41 05  INC  $0541
031EDA  b24:$DECA  A9 0F     LDA  #$0F
031EDC  b24:$DECC  8D 15 01  STA  $0115
031EDF  b24:$DECF  8D 16 01  STA  $0116
031EE2  b24:$DED2  8D 17 01  STA  $0117
031EE5  b24:$DED5  60        RTS
031EE6  b24:$DED6  EE 40 05  INC  $0540
031EE9  b24:$DED9  A9 00     LDA  #$00
031EEB  b24:$DEDB  8D 41 05  STA  $0541
031EEE  b24:$DEDE  A9 B0     LDA  #$B0
031EF0  b24:$DEE0  85 CE     STA  $CE
031EF2  b24:$DEE2  A9 04     LDA  #$04
031EF4  b24:$DEE4  85 D6     STA  $D6
031EF6  b24:$DEE6  A9 00     LDA  #$00
031EF8  b24:$DEE8  8D 44 05  STA  $0544
031EFB  b24:$DEEB  8D 70 04  STA  $0470
031EFE  b24:$DEEE  8D 71 04  STA  $0471
031F01  b24:$DEF1  20 7F E5  JSR  $E57F
031F04  b24:$DEF4  A9 B0     LDA  #$B0
031F06  b24:$DEF6  20 73 E6  JSR  $E673
031F09  b24:$DEF9  60        RTS
031F0A  b24:$DEFA  0A        ASL  A
031F0B  b24:$DEFB  A8        TAY
031F0C  b24:$DEFC  B9 EF 97  LDA  $97EF,Y
031F0F  b24:$DEFF  85 00     STA  $00
031F11  b24:$DF01  B9 F0 97  LDA  $97F0,Y
031F14  b24:$DF04  85 01     STA  $01
031F16  b24:$DF06  A9 58     LDA  #$58
031F18  b24:$DF08  85 0A     STA  $0A
031F1A  b24:$DF0A  A9 68     LDA  #$68
031F1C  b24:$DF0C  85 0C     STA  $0C
031F1E  b24:$DF0E  A9 01     LDA  #$01
031F20  b24:$DF10  85 02     STA  $02
031F22  b24:$DF12  4C AD F1  JMP  $F1AD

; five_phase_inline_pointer_table: physical24 $DE3A..$DE43, file0x031E4A, inline_pointer_data
031E4A b24:$DE3A .byte $44,$DE,$66,$DE,$B9,$DE,$C7,$DE,$D6,$DE ; DATA

; original24_frame_sequence_andFF_terminator: physical24 $DEA0..$DEB8, file0x031EB0, data
031EB0 b24:$DEA0 .byte $00,$01,$02,$03,$04,$05,$06,$07,$08,$08,$08,$08,$08,$08,$08,$08 ; DATA
031EC0 b24:$DEB0 .byte $09,$0A,$0B,$0C,$0D,$0E,$0D,$08,$FF ; DATA

; sprite_descriptor15_pointer_table: physical1 $97EF..$980C, file0x0037FF, data
0037FF b1:$97EF .byte $0D,$98,$12,$98,$17,$98,$24,$98,$41,$98,$52,$98,$7B,$98,$94,$98 ; DATA
00380F b1:$97FF .byte $C5,$98,$E2,$98,$FF,$98,$1C,$99,$39,$99,$56,$99,$7B,$99 ; DATA

; original_intro_sprite_frame0: physical1 $980D..$9811, file0x00381D, sprite_data
00381D b1:$980D .byte $20,$01,$00,$18,$80 ; DATA

; original_intro_sprite_frame1: physical1 $9812..$9816, file0x003822, sprite_data
003822 b1:$9812 .byte $20,$02,$00,$18,$80 ; DATA

; original_intro_sprite_frame2: physical1 $9817..$9823, file0x003827, sprite_data
003827 b1:$9817 .byte $18,$04,$00,$18,$20,$05,$00,$18,$28,$06,$00,$18,$80 ; DATA

; original_intro_sprite_frame3: physical1 $9824..$9840, file0x003834, sprite_data
003834 b1:$9824 .byte $18,$06,$00,$10,$18,$07,$00,$18,$20,$08,$00,$10,$20,$09,$00,$18 ; DATA
003844 b1:$9834 .byte $20,$0A,$00,$20,$28,$0B,$00,$18,$28,$0C,$00,$20,$80 ; DATA

; original_intro_sprite_frame4: physical1 $9841..$9851, file0x003851, sprite_data
003851 b1:$9841 .byte $20,$0D,$00,$10,$20,$0E,$00,$18,$20,$0F,$00,$20,$20,$10,$00,$28 ; DATA
003861 b1:$9851 .byte $80 ; DATA

; original_intro_sprite_frame5: physical1 $9852..$987A, file0x003862, sprite_data
003862 b1:$9852 .byte $10,$11,$00,$20,$18,$12,$00,$18,$18,$13,$00,$20,$18,$14,$00,$28 ; DATA
003872 b1:$9862 .byte $20,$15,$00,$10,$20,$16,$00,$18,$20,$17,$00,$20,$28,$18,$00,$10 ; DATA
003882 b1:$9872 .byte $28,$19,$00,$18,$30,$1A,$00,$10,$80 ; DATA

; original_intro_sprite_frame6: physical1 $987B..$9893, file0x00388B, sprite_data
00388B b1:$987B .byte $08,$1B,$00,$18,$10,$1C,$00,$18,$18,$1D,$00,$18,$20,$1E,$00,$18 ; DATA
00389B b1:$988B .byte $28,$1F,$00,$18,$30,$20,$00,$18,$80 ; DATA

; original_intro_sprite_frame7: physical1 $9894..$98C4, file0x0038A4, sprite_data
0038A4 b1:$9894 .byte $10,$21,$00,$08,$10,$22,$00,$10,$18,$23,$00,$08,$18,$24,$00,$10 ; DATA
0038B4 b1:$98A4 .byte $18,$25,$00,$18,$20,$26,$00,$10,$20,$27,$00,$18,$20,$28,$00,$20 ; DATA
0038C4 b1:$98B4 .byte $28,$29,$00,$18,$28,$2A,$00,$20,$28,$2B,$00,$28,$30,$2C,$00,$28 ; DATA
0038D4 b1:$98C4 .byte $80 ; DATA

; original_intro_sprite_frame8: physical1 $98C5..$98E1, file0x0038D5, sprite_data
0038D5 b1:$98C5 .byte $20,$2D,$00,$00,$20,$2E,$00,$08,$20,$2F,$00,$10,$20,$30,$00,$18 ; DATA
0038E5 b1:$98D5 .byte $20,$31,$00,$20,$20,$32,$00,$28,$20,$33,$00,$30,$80 ; DATA

; original_intro_sprite_frame9: physical1 $98E2..$98FE, file0x0038F2, sprite_data
0038F2 b1:$98E2 .byte $20,$2D,$00,$00,$20,$2E,$00,$08,$20,$2F,$00,$10,$20,$30,$00,$18 ; DATA
003902 b1:$98F2 .byte $20,$31,$00,$20,$20,$32,$00,$28,$20,$34,$00,$30,$80 ; DATA

; original_intro_sprite_frame10: physical1 $98FF..$991B, file0x00390F, sprite_data
00390F b1:$98FF .byte $20,$2D,$00,$00,$20,$2E,$00,$08,$20,$2F,$00,$10,$20,$30,$00,$18 ; DATA
00391F b1:$990F .byte $20,$31,$00,$20,$20,$32,$00,$28,$20,$35,$00,$30,$80 ; DATA

; original_intro_sprite_frame11: physical1 $991C..$9938, file0x00392C, sprite_data
00392C b1:$991C .byte $20,$2D,$00,$00,$20,$2E,$00,$08,$20,$2F,$00,$10,$20,$30,$00,$18 ; DATA
00393C b1:$992C .byte $20,$31,$00,$20,$20,$32,$00,$28,$20,$36,$00,$30,$80 ; DATA

; original_intro_sprite_frame12: physical1 $9939..$9955, file0x003949, sprite_data
003949 b1:$9939 .byte $20,$2D,$00,$00,$20,$2E,$00,$08,$20,$2F,$00,$10,$20,$30,$00,$18 ; DATA
003959 b1:$9949 .byte $20,$31,$00,$20,$20,$32,$00,$28,$20,$37,$00,$30,$80 ; DATA

; original_intro_sprite_frame13: physical1 $9956..$997A, file0x003966, sprite_data
003966 b1:$9956 .byte $20,$2D,$00,$00,$20,$2E,$00,$08,$20,$2F,$00,$10,$20,$30,$00,$18 ; DATA
003976 b1:$9966 .byte $20,$31,$00,$20,$20,$32,$00,$28,$20,$38,$00,$30,$18,$39,$00,$30 ; DATA
003986 b1:$9976 .byte $20,$3A,$00,$38,$80 ; DATA

; original_intro_sprite_frame14: physical1 $997B..$999F, file0x00398B, sprite_data
00398B b1:$997B .byte $20,$2D,$00,$00,$20,$2E,$00,$08,$20,$2F,$00,$10,$20,$30,$00,$18 ; DATA
00399B b1:$998B .byte $20,$31,$00,$20,$20,$32,$00,$28,$20,$3B,$00,$30,$18,$3C,$00,$30 ; DATA
0039AB b1:$999B .byte $20,$3D,$00,$38,$80 ; DATA

