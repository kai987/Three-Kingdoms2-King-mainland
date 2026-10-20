; New28 readonly originalbytes; fileoffsets include16byteheader
; bank8 file$010016
$A006: 4C B3 BA  ; JMP ab $BAB3
; bank8 file$011AC3
$BAB3: AD 01 05  ; LDA ab $0501
; bank8 file$011AC6
$BAB6: 20 DE EA  ; JSR ab $EADE
; bank8 file$011AD1
$BAC1: A9 08     ; LDA im $0008
; bank8 file$011AD3
$BAC3: 8D B2 00  ; STA ab $00B2
; bank8 file$011AD6
$BAC6: 8D C2 00  ; STA ab $00C2
; bank8 file$011AD9
$BAC9: 8D CA 00  ; STA ab $00CA
; bank8 file$011ADC
$BACC: 8D D2 00  ; STA ab $00D2
; bank8 file$011ADF
$BACF: 8D DA 00  ; STA ab $00DA
; bank8 file$011AE2
$BAD2: A9 09     ; LDA im $0009
; bank8 file$011AE4
$BAD4: 8D B3 00  ; STA ab $00B3
; bank8 file$011AE7
$BAD7: 8D C3 00  ; STA ab $00C3
; bank8 file$011AEA
$BADA: 8D CB 00  ; STA ab $00CB
; bank8 file$011AED
$BADD: 8D D3 00  ; STA ab $00D3
; bank8 file$011AF0
$BAE0: 8D DB 00  ; STA ab $00DB
; bank8 file$011AF3
$BAE3: AD 07 05  ; LDA ab $0507
; bank8 file$011AF6
$BAE6: 4A        ; LSR a $0000
; bank8 file$011AF7
$BAE7: 4A        ; LSR a $0000
; bank8 file$011AF8
$BAE8: 4A        ; LSR a $0000
; bank8 file$011AF9
$BAE9: 4A        ; LSR a $0000
; bank8 file$011AFA
$BAEA: 20 68 F3  ; JSR ab $F368
; bank8 file$011AFD
$BAED: A0 03     ; LDY im $0003
; bank8 file$011AFF
$BAEF: B1 00     ; LDA iy $0000
; bank8 file$011B01
$BAF1: C9 03     ; CMP im $0003
; bank8 file$011B03
$BAF3: F0 2A     ; BEQ rel $002A
; bank8 file$011B05
$BAF5: 8D 44 6F  ; STA ab $6F44
; bank8 file$011B08
$BAF8: AD 14 05  ; LDA ab $0514
; bank8 file$011B0B
$BAFB: F0 12     ; BEQ rel $0012
; bank8 file$011B0D
$BAFD: A9 0A     ; LDA im $000A
; bank8 file$011B0F
$BAFF: A9 0D     ; LDA im $000D
; bank8 file$011B11
$BB01: 8D 00 05  ; STA ab $0500
; bank8 file$011B14
$BB04: A9 00     ; LDA im $0000
; bank8 file$011B16
$BB06: 8D 01 05  ; STA ab $0501
; bank8 file$011B19
$BB09: A9 11     ; LDA im $0011
; bank8 file$011B1B
$BB0B: 8D 0B 05  ; STA ab $050B
; bank8 file$011B1E
$BB0E: 60        ; RTS i $0000
; bank8 file$011B1F
$BB0F: A9 0E     ; LDA im $000E
; bank8 file$011B21
$BB11: 8D 00 05  ; STA ab $0500
; bank8 file$011B24
$BB14: A9 00     ; LDA im $0000
; bank8 file$011B26
$BB16: 8D 01 05  ; STA ab $0501
; bank8 file$011B29
$BB19: A9 11     ; LDA im $0011
; bank8 file$011B2B
$BB1B: 8D 0B 05  ; STA ab $050B
; bank8 file$011B2E
$BB1E: 60        ; RTS i $0000
; bank8 file$011B2F
$BB1F: A9 80     ; LDA im $0080
; bank8 file$011B31
$BB21: 8D 04 05  ; STA ab $0504
; bank8 file$011B34
$BB24: AD 14 05  ; LDA ab $0514
; bank8 file$011B37
$BB27: F0 08     ; BEQ rel $0008
; bank8 file$011B39
$BB29: A9 02     ; LDA im $0002
; bank8 file$011B3B
$BB2B: 8D 91 6F  ; STA ab $6F91
; bank8 file$011B3E
$BB2E: 4C 36 BB  ; JMP ab $BB36
; bank8 file$011B41
$BB31: A9 00     ; LDA im $0000
; bank8 file$011B43
$BB33: 8D 91 6F  ; STA ab $6F91
; bank8 file$011B46
$BB36: 20 46 BC  ; JSR ab $BC46
; bank8 file$011B49
$BB39: EE 01 05  ; INC ab $0501
; bank8 file$011B4C
$BB3C: 60        ; RTS i $0000
; bank8 file$011B4D
$BB3D: AD 07 05  ; LDA ab $0507
; bank8 file$011B50
$BB40: 29 0F     ; AND im $000F
; bank8 file$011B52
$BB42: 20 68 F3  ; JSR ab $F368
; bank8 file$011B55
$BB45: A0 03     ; LDY im $0003
; bank8 file$011B57
$BB47: B1 00     ; LDA iy $0000
; bank8 file$011B59
$BB49: C9 03     ; CMP im $0003
; bank8 file$011B5B
$BB4B: F0 28     ; BEQ rel $0028
; bank8 file$011B5D
$BB4D: 8D 44 6F  ; STA ab $6F44
; bank8 file$011B60
$BB50: AD 14 05  ; LDA ab $0514
; bank8 file$011B63
$BB53: D0 10     ; BNE rel $0010
; bank8 file$011B65
$BB55: A9 0D     ; LDA im $000D
; bank8 file$011B67
$BB57: 8D 00 05  ; STA ab $0500
; bank8 file$011B6A
$BB5A: A9 00     ; LDA im $0000
; bank8 file$011B6C
$BB5C: 8D 01 05  ; STA ab $0501
; bank8 file$011B6F
$BB5F: A9 02     ; LDA im $0002
; bank8 file$011B71
$BB61: 8D 0B 05  ; STA ab $050B
; bank8 file$011B74
$BB64: 60        ; RTS i $0000
; bank8 file$011B75
$BB65: A9 0E     ; LDA im $000E
; bank8 file$011B77
$BB67: 8D 00 05  ; STA ab $0500
; bank8 file$011B7A
$BB6A: A9 00     ; LDA im $0000
; bank8 file$011B7C
$BB6C: 8D 01 05  ; STA ab $0501
; bank8 file$011B7F
$BB6F: A9 02     ; LDA im $0002
; bank8 file$011B81
$BB71: 8D 0B 05  ; STA ab $050B
; bank8 file$011B84
$BB74: 60        ; RTS i $0000
; bank8 file$011B85
$BB75: A9 00     ; LDA im $0000
; bank8 file$011B87
$BB77: 8D 04 05  ; STA ab $0504
; bank8 file$011B8A
$BB7A: AD 14 05  ; LDA ab $0514
; bank8 file$011B8D
$BB7D: D0 08     ; BNE rel $0008
; bank8 file$011B8F
$BB7F: A9 01     ; LDA im $0001
; bank8 file$011B91
$BB81: 8D 91 6F  ; STA ab $6F91
; bank8 file$011B94
$BB84: 4C 8C BB  ; JMP ab $BB8C
; bank8 file$011B97
$BB87: A9 00     ; LDA im $0000
; bank8 file$011B99
$BB89: 8D 91 6F  ; STA ab $6F91
; bank8 file$011B9C
$BB8C: 20 46 BC  ; JSR ab $BC46
; bank8 file$011B9F
$BB8F: EE 01 05  ; INC ab $0501
; bank8 file$011BA2
$BB92: 60        ; RTS i $0000
; bank8 file$011BA3
$BB93: 20 EE EC  ; JSR ab $ECEE
; bank8 file$011BA6
$BB96: 20 0A BF  ; JSR ab $BF0A
; bank8 file$011BA9
$BB99: 20 27 C0  ; JSR ab $C027
; bank8 file$011BAC
$BB9C: EE 01 05  ; INC ab $0501
; bank8 file$011BAF
$BB9F: 60        ; RTS i $0000
; bank8 file$011BB0
$BBA0: AD 87 00  ; LDA ab $0087
; bank8 file$011BB3
$BBA3: 10 12     ; BPL rel $0012
; bank8 file$011BB5
$BBA5: 20 B8 BB  ; JSR ab $BBB8
; bank8 file$011BB8
$BBA8: A9 01     ; LDA im $0001
; bank8 file$011BBA
$BBAA: 8D 7A 00  ; STA ab $007A
; bank8 file$011BBD
$BBAD: A9 0D     ; LDA im $000D
; bank8 file$011BBF
$BBAF: 8D 00 04  ; STA ab $0400
; bank8 file$011BC2
$BBB2: A9 00     ; LDA im $0000
; bank8 file$011BC4
$BBB4: 8D 01 04  ; STA ab $0401
; bank8 file$011BC7
$BBB7: 60        ; RTS i $0000
; bank13 file$01B500
$D4F0: 20 29 CC  ; JSR ab $CC29
; bank13 file$01B503
$D4F3: A0 28     ; LDY im $0028
; bank13 file$01B505
$D4F5: 20 07 EE  ; JSR ab $EE07
; bank13 file$01B50A
$D4FA: 60        ; RTS i $0000
; bank31 file$03EC77
$EC67: AD 87 00  ; LDA ab $0087
; bank31 file$03EC7A
$EC6A: 30 52     ; BMI rel $0052
; bank31 file$03EC7C
$EC6C: CE 8A 00  ; DEC ab $008A
; bank31 file$03EC7F
$EC6F: 10 4D     ; BPL rel $004D
; bank31 file$03EC81
$EC71: AD 89 00  ; LDA ab $0089
; bank31 file$03EC84
$EC74: 8D 8A 00  ; STA ab $008A
; bank31 file$03EC87
$EC77: A9 01     ; LDA im $0001
; bank31 file$03EC89
$EC79: 8D 7D 00  ; STA ab $007D
; bank31 file$03EC8C
$EC7C: AD 87 00  ; LDA ab $0087
; bank31 file$03EC8F
$EC7F: F0 0D     ; BEQ rel $000D
; bank31 file$03EC91
$EC81: EE 88 00  ; INC ab $0088
; bank31 file$03EC94
$EC84: AD 88 00  ; LDA ab $0088
; bank31 file$03EC97
$EC87: C9 04     ; CMP im $0004
; bank31 file$03EC99
$EC89: 90 0D     ; BCC rel $000D
; bank31 file$03EC9B
$EC8B: 4C 93 EC  ; JMP ab $EC93
; bank31 file$03EC9E
$EC8E: CE 88 00  ; DEC ab $0088
; bank31 file$03ECA1
$EC91: D0 05     ; BNE rel $0005
; bank31 file$03ECA3
$EC93: A9 FF     ; LDA im $00FF
; bank31 file$03ECA5
$EC95: 8D 87 00  ; STA ab $0087
; bank31 file$03ECA8
$EC98: A9 00     ; LDA im $0000
; bank31 file$03ECAA
$EC9A: 85 00     ; STA zp $0000
; bank31 file$03ECAC
$EC9C: A9 01     ; LDA im $0001
; bank31 file$03ECAE
$EC9E: 85 01     ; STA zp $0001
; bank31 file$03ECB0
$ECA0: A9 20     ; LDA im $0020
; bank31 file$03ECB2
$ECA2: 85 02     ; STA zp $0002
; bank31 file$03ECB4
$ECA4: A9 01     ; LDA im $0001
; bank31 file$03ECB6
$ECA6: 85 03     ; STA zp $0003
; bank31 file$03ECB8
$ECA8: A0 1F     ; LDY im $001F
; bank31 file$03ECBA
$ECAA: AE 88 00  ; LDX ab $0088
; bank31 file$03ECBD
$ECAD: B1 02     ; LDA iy $0002
; bank31 file$03ECBF
$ECAF: CA        ; DEX i $0000
; bank31 file$03ECC0
$ECB0: 30 07     ; BMI rel $0007
; bank31 file$03ECC2
$ECB2: 38        ; SEC i $0000
; bank31 file$03ECC3
$ECB3: E9 10     ; SBC im $0010
; bank31 file$03ECC5
$ECB5: 10 F8     ; BPL rel $00F8
; bank31 file$03ECC7
$ECB7: A9 0F     ; LDA im $000F
; bank31 file$03ECC9
$ECB9: 91 00     ; STA iy $0000
; bank31 file$03ECCB
$ECBB: 88        ; DEY i $0000
; bank31 file$03ECCC
$ECBC: 10 EC     ; BPL rel $00EC
; bank31 file$03ECCE
$ECBE: 60        ; RTS i $0000
; bank31 file$03ECCF
$ECBF: A9 00     ; LDA im $0000
; bank31 file$03ECD1
$ECC1: 8D 87 00  ; STA ab $0087
; bank31 file$03ECD4
$ECC4: A9 04     ; LDA im $0004
; bank31 file$03ECD6
$ECC6: 8D 88 00  ; STA ab $0088
; bank31 file$03ECD9
$ECC9: A9 04     ; LDA im $0004
; bank31 file$03ECDB
$ECCB: 8D 89 00  ; STA ab $0089
; bank31 file$03ECDE
$ECCE: A9 00     ; LDA im $0000
; bank31 file$03ECE0
$ECD0: 85 00     ; STA zp $0000
; bank31 file$03ECE2
$ECD2: A9 01     ; LDA im $0001
; bank31 file$03ECE4
$ECD4: 85 01     ; STA zp $0001
; bank31 file$03ECE6
$ECD6: A9 20     ; LDA im $0020
; bank31 file$03ECE8
$ECD8: 85 02     ; STA zp $0002
; bank31 file$03ECEA
$ECDA: A9 01     ; LDA im $0001
; bank31 file$03ECEC
$ECDC: 85 03     ; STA zp $0003
; bank31 file$03ECEE
$ECDE: A0 00     ; LDY im $0000
; bank31 file$03ECF0
$ECE0: B1 00     ; LDA iy $0000
; bank31 file$03ECF2
$ECE2: 91 02     ; STA iy $0002
; bank31 file$03ECF4
$ECE4: A9 0F     ; LDA im $000F
; bank31 file$03ECF6
$ECE6: 91 00     ; STA iy $0000
; bank31 file$03ECF8
$ECE8: C8        ; INY i $0000
; bank31 file$03ECF9
$ECE9: C0 20     ; CPY im $0020
; bank31 file$03ECFB
$ECEB: 90 F3     ; BCC rel $00F3
; bank31 file$03ECFD
$ECED: 60        ; RTS i $0000
; bank31 file$03ECFE
$ECEE: A9 01     ; LDA im $0001
; bank31 file$03ED00
$ECF0: 8D 87 00  ; STA ab $0087
; bank31 file$03ED03
$ECF3: A9 00     ; LDA im $0000
; bank31 file$03ED05
$ECF5: 8D 88 00  ; STA ab $0088
; bank31 file$03ED08
$ECF8: A9 04     ; LDA im $0004
; bank31 file$03ED0A
$ECFA: 8D 89 00  ; STA ab $0089
; bank31 file$03ED0D
$ECFD: A9 00     ; LDA im $0000
; bank31 file$03ED0F
$ECFF: 85 00     ; STA zp $0000
; bank31 file$03ED11
$ED01: A9 01     ; LDA im $0001
; bank31 file$03ED13
$ED03: 85 01     ; STA zp $0001
; bank31 file$03ED15
$ED05: A9 20     ; LDA im $0020
; bank31 file$03ED17
$ED07: 85 02     ; STA zp $0002
; bank31 file$03ED19
$ED09: A9 01     ; LDA im $0001
; bank31 file$03ED1B
$ED0B: 85 03     ; STA zp $0003
; bank31 file$03ED1D
$ED0D: A0 00     ; LDY im $0000
; bank31 file$03ED1F
$ED0F: B1 00     ; LDA iy $0000
; bank31 file$03ED21
$ED11: 91 02     ; STA iy $0002
; bank31 file$03ED23
$ED13: C8        ; INY i $0000
; bank31 file$03ED24
$ED14: C0 20     ; CPY im $0020
; bank31 file$03ED26
$ED16: 90 F7     ; BCC rel $00F7
; bank31 file$03ED28
$ED18: 60        ; RTS i $0000
; bank31 file$03EE17
$EE07: AD E2 00  ; LDA ab $00E2
; bank31 file$03EE1A
$EE0A: 8D 58 00  ; STA ab $0058
; bank31 file$03EE1D
$EE0D: 8C 5D 00  ; STY ab $005D
; bank31 file$03EE20
$EE10: 68        ; PLA i $0000
; bank31 file$03EE21
$EE11: 18        ; CLC i $0000
; bank31 file$03EE22
$EE12: 69 01     ; ADC im $0001
; bank31 file$03EE24
$EE14: 8D 59 00  ; STA ab $0059
; bank31 file$03EE27
$EE17: 68        ; PLA i $0000
; bank31 file$03EE28
$EE18: 69 00     ; ADC im $0000
; bank31 file$03EE2A
$EE1A: 8D 5A 00  ; STA ab $005A
; bank31 file$03EE2D
$EE1D: A0 00     ; LDY im $0000
; bank31 file$03EE2F
$EE1F: B1 59     ; LDA iy $0059
; bank31 file$03EE31
$EE21: 8D 5B 00  ; STA ab $005B
; bank31 file$03EE34
$EE24: C8        ; INY i $0000
; bank31 file$03EE35
$EE25: B1 59     ; LDA iy $0059
; bank31 file$03EE37
$EE27: 8D 5C 00  ; STA ab $005C
; bank31 file$03EE3A
$EE2A: AC 5D 00  ; LDY ab $005D
; bank31 file$03EE3D
$EE2D: 20 37 F2  ; JSR ab $F237
; bank31 file$03EE40
$EE30: EE 59 00  ; INC ab $0059
; bank31 file$03EE43
$EE33: D0 03     ; BNE rel $0003
; bank31 file$03EE45
$EE35: EE 5A 00  ; INC ab $005A
; bank31 file$03EE48
$EE38: AD 5A 00  ; LDA ab $005A
; bank31 file$03EE4B
$EE3B: 48        ; PHA i $0000
; bank31 file$03EE4C
$EE3C: AD 59 00  ; LDA ab $0059
; bank31 file$03EE4F
$EE3F: 48        ; PHA i $0000
; bank31 file$03EE50
$EE40: AD 58 00  ; LDA ab $0058
; bank31 file$03EE53
$EE43: 48        ; PHA i $0000
; bank31 file$03EE54
$EE44: A9 EE     ; LDA im $00EE
; bank31 file$03EE56
$EE46: 48        ; PHA i $0000
; bank31 file$03EE57
$EE47: A9 4C     ; LDA im $004C
; bank31 file$03EE59
$EE49: 48        ; PHA i $0000
; bank31 file$03EE5A
$EE4A: 6C 5B 00  ; JMP ind $005B
; bank31 file$03EE5D
$EE4D: 68        ; PLA i $0000
; bank31 file$03EE5E
$EE4E: A8        ; TAY i $0000
; bank31 file$03EE5F
$EE4F: 20 37 F2  ; JSR ab $F237
; bank31 file$03EE62
$EE52: 60        ; RTS i $0000
; bank31 file$03F90E
$F8FE: 20 53 EE  ; JSR ab $EE53
; bank31 file$03F911
$F901: 20 06 F2  ; JSR ab $F206
; bank31 file$03F914
$F904: 20 0B FB  ; JSR ab $FB0B
; bank31 file$03F917
$F907: A9 00     ; LDA im $0000
; bank31 file$03F919
$F909: 85 7C     ; STA zp $007C
; bank31 file$03F91B
$F90B: 20 67 EC  ; JSR ab $EC67
; bank31 file$03F91E
$F90E: 20 C6 E6  ; JSR ab $E6C6
; bank31 file$03F921
$F911: A0 2E     ; LDY im $002E
; bank31 file$03F923
$F913: 20 37 F2  ; JSR ab $F237
; bank31 file$03F926
$F916: 20 03 A0  ; JSR ab $A003
; bank31 file$03F929
$F919: A9 4C     ; LDA im $004C
; bank31 file$03F92B
$F91B: 85 A5     ; STA zp $00A5
; bank31 file$03F92D
$F91D: 8D 00 F8  ; STA ab $F800
; bank31 file$03F930
$F920: 20 62 FF  ; JSR ab $FF62
; bank31 file$03F933
$F923: AD 00 05  ; LDA ab $0500
; bank31 file$03F936
$F926: C9 0C     ; CMP im $000C
; bank31 file$03F938
$F928: B0 13     ; BCS rel $0013
; bank31 file$03F93A
$F92A: AD 8F 00  ; LDA ab $008F
; bank31 file$03F93D
$F92D: D0 0E     ; BNE rel $000E
; bank31 file$03F93F
$F92F: 20 77 F0  ; JSR ab $F077
; bank31 file$03F942
$F932: A0 37     ; LDY im $0037
; bank31 file$03F944
$F934: 20 37 F2  ; JSR ab $F237
; bank31 file$03F947
$F937: 20 0C A0  ; JSR ab $A00C
; bank31 file$03F94A
$F93A: 20 0F A0  ; JSR ab $A00F
; bank31 file$03F94D
$F93D: 20 A9 FA  ; JSR ab $FAA9
; bank31 file$03F950
$F940: A0 39     ; LDY im $0039
; bank31 file$03F952
$F942: 20 37 F2  ; JSR ab $F237
; bank31 file$03F955
$F945: 20 0F A0  ; JSR ab $A00F
; bank31 file$03F958
$F948: A0 2C     ; LDY im $002C
; bank31 file$03F95A
$F94A: 20 37 F2  ; JSR ab $F237
; bank31 file$03F95D
$F94D: 20 00 A0  ; JSR ab $A000
; bank31 file$03F960
$F950: A0 3D     ; LDY im $003D
; bank31 file$03F962
$F952: 20 37 F2  ; JSR ab $F237
; bank31 file$03F965
$F955: 20 03 A0  ; JSR ab $A003
; bank31 file$03F968
$F958: 20 BF FA  ; JSR ab $FABF
; bank31 file$03F96B
$F95B: 20 30 E8  ; JSR ab $E830
