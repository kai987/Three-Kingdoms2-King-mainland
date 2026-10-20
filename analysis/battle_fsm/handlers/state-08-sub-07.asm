; main=8 sub=7: 电脑方行动桥接
; entry bank12 $BFDC; file $019FEC
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0183E2 b12:$A3D2 A9 00          LDA  #$00
0183E4 b12:$A3D4 8D 44 05       STA  $0544
0183E7 b12:$A3D7 AC 0A 05       LDY  $050A
0183EA b12:$A3DA A2 00          LDX  #$00
0183EC b12:$A3DC 20 33 A4       JSR  $A433 ; save_attack_officer_stats
0183EF b12:$A3DF AC 09 05       LDY  $0509
0183F2 b12:$A3E2 A2 01          LDX  #$01
0183F4 b12:$A3E4 A9 00          LDA  #$00
0183F6 b12:$A3E6 99 50 06       STA  $0650,Y
0183F9 b12:$A3E9 20 33 A4       JSR  $A433 ; save_attack_officer_stats
0183FC b12:$A3EC AD 04 05       LDA  $0504
0183FF b12:$A3EF 30 15          BMI  $A406
018401 b12:$A3F1 AD 07 05       LDA  $0507
018404 b12:$A3F4 29 0F          AND  #$0F
018406 b12:$A3F6 8D 64 05       STA  $0564
018409 b12:$A3F9 AD 07 05       LDA  $0507
01840C b12:$A3FC 4A             LSR  A
01840D b12:$A3FD 4A             LSR  A
01840E b12:$A3FE 4A             LSR  A
01840F b12:$A3FF 4A             LSR  A
018410 b12:$A400 8D 65 05       STA  $0565
018413 b12:$A403 4C 18 A4       JMP  $A418
018416 b12:$A406 AD 07 05       LDA  $0507
018419 b12:$A409 29 0F          AND  #$0F
01841B b12:$A40B 8D 65 05       STA  $0565
01841E b12:$A40E AD 07 05       LDA  $0507
018421 b12:$A411 4A             LSR  A
018422 b12:$A412 4A             LSR  A
018423 b12:$A413 4A             LSR  A
018424 b12:$A414 4A             LSR  A
018425 b12:$A415 8D 64 05       STA  $0564
018428 b12:$A418 AD 64 05       LDA  $0564
01842B b12:$A41B 20 68 F3       JSR  $F368 ; ruler_record_pointer
01842E b12:$A41E A0 03          LDY  #$03
018430 b12:$A420 B1 00          LDA  ($00),Y
018432 b12:$A422 8D 62 05       STA  $0562
018435 b12:$A425 AD 65 05       LDA  $0565
018438 b12:$A428 20 68 F3       JSR  $F368 ; ruler_record_pointer
01843B b12:$A42B A0 03          LDY  #$03
01843D b12:$A42D B1 00          LDA  ($00),Y
01843F b12:$A42F 8D 63 05       STA  $0563
018442 b12:$A432 60             RTS
019FEC b12:$BFDC AC 8D 6F       LDY  $6F8D
019FEF b12:$BFDF 20 36 DC       JSR  $DC36 ; draw_officer_by_slot
019FF2 b12:$BFE2 AD 87 00       LDA  $0087
019FF5 b12:$BFE5 10 1C          BPL  $C003
019FF7 b12:$BFE7 AD 8D 6F       LDA  $6F8D
019FFA b12:$BFEA 8D 09 05       STA  $0509
019FFD b12:$BFED AD 8C 6F       LDA  $6F8C
01A000 b12:$BFF0 8D 0A 05       STA  $050A
01A003 b12:$BFF3 A9 03          LDA  #$03
01A005 b12:$BFF5 8D 00 05       STA  $0500
01A008 b12:$BFF8 8D 01 05       STA  $0501
01A00B b12:$BFFB A9 00          LDA  #$00
01A00D b12:$BFFD 8D A4 00       STA  $00A4
01A010 b13:$C000 4C D2 A3       JMP  $A3D2
01A013 b13:$C003 60             RTS
