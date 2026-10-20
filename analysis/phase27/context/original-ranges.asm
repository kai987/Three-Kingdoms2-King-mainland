; phase27 G106 original trusted instructions; all file offsets include16-byte iNES header
; bank08 file $010016
$A006: 4C B3 BA  ; JMP ab $BAB3
; bank08 file $011AC3
$BAB3: AD 01 05  ; LDA ab $0501
; bank08 file $011AC6
$BAB6: 20 DE EA  ; JSR ab $EADE
; bank08 file $011AD1
$BAC1: A9 08     ; LDA im $0008
; bank08 file $011AD3
$BAC3: 8D B2 00  ; STA ab $00B2
; bank08 file $011AD6
$BAC6: 8D C2 00  ; STA ab $00C2
; bank08 file $011AD9
$BAC9: 8D CA 00  ; STA ab $00CA
; bank08 file $011ADC
$BACC: 8D D2 00  ; STA ab $00D2
; bank08 file $011ADF
$BACF: 8D DA 00  ; STA ab $00DA
; bank08 file $011AE2
$BAD2: A9 09     ; LDA im $0009
; bank08 file $011AE4
$BAD4: 8D B3 00  ; STA ab $00B3
; bank08 file $011AE7
$BAD7: 8D C3 00  ; STA ab $00C3
; bank08 file $011AEA
$BADA: 8D CB 00  ; STA ab $00CB
; bank08 file $011AED
$BADD: 8D D3 00  ; STA ab $00D3
; bank08 file $011AF0
$BAE0: 8D DB 00  ; STA ab $00DB
; bank08 file $011AF3
$BAE3: AD 07 05  ; LDA ab $0507
; bank08 file $011AF6
$BAE6: 4A        ; LSR a $0000
; bank08 file $011AF7
$BAE7: 4A        ; LSR a $0000
; bank08 file $011AF8
$BAE8: 4A        ; LSR a $0000
; bank08 file $011AF9
$BAE9: 4A        ; LSR a $0000
; bank08 file $011AFA
$BAEA: 20 68 F3  ; JSR ab $F368
; bank08 file $011AFD
$BAED: A0 03     ; LDY im $0003
; bank08 file $011AFF
$BAEF: B1 00     ; LDA iy $0000
; bank08 file $011B01
$BAF1: C9 03     ; CMP im $0003
; bank08 file $011B03
$BAF3: F0 2A     ; BEQ rel $002A
; bank08 file $011B05
$BAF5: 8D 44 6F  ; STA ab $6F44
; bank08 file $011B08
$BAF8: AD 14 05  ; LDA ab $0514
; bank08 file $011B0B
$BAFB: F0 12     ; BEQ rel $0012
; bank08 file $011B0D
$BAFD: A9 0A     ; LDA im $000A
; bank08 file $011B0F
$BAFF: A9 0D     ; LDA im $000D
; bank08 file $011B11
$BB01: 8D 00 05  ; STA ab $0500
; bank08 file $011B14
$BB04: A9 00     ; LDA im $0000
; bank08 file $011B16
$BB06: 8D 01 05  ; STA ab $0501
; bank08 file $011B19
$BB09: A9 11     ; LDA im $0011
; bank08 file $011B1B
$BB0B: 8D 0B 05  ; STA ab $050B
; bank08 file $011B1E
$BB0E: 60        ; RTS i $0000
; bank08 file $011B1F
$BB0F: A9 0E     ; LDA im $000E
; bank08 file $011B21
$BB11: 8D 00 05  ; STA ab $0500
; bank08 file $011B24
$BB14: A9 00     ; LDA im $0000
; bank08 file $011B26
$BB16: 8D 01 05  ; STA ab $0501
; bank08 file $011B29
$BB19: A9 11     ; LDA im $0011
; bank08 file $011B2B
$BB1B: 8D 0B 05  ; STA ab $050B
; bank08 file $011B2E
$BB1E: 60        ; RTS i $0000
; bank08 file $011B2F
$BB1F: A9 80     ; LDA im $0080
; bank08 file $011B31
$BB21: 8D 04 05  ; STA ab $0504
; bank08 file $011B34
$BB24: AD 14 05  ; LDA ab $0514
; bank08 file $011B37
$BB27: F0 08     ; BEQ rel $0008
; bank08 file $011B39
$BB29: A9 02     ; LDA im $0002
; bank08 file $011B3B
$BB2B: 8D 91 6F  ; STA ab $6F91
; bank08 file $011B3E
$BB2E: 4C 36 BB  ; JMP ab $BB36
; bank08 file $011B41
$BB31: A9 00     ; LDA im $0000
; bank08 file $011B43
$BB33: 8D 91 6F  ; STA ab $6F91
; bank08 file $011B46
$BB36: 20 46 BC  ; JSR ab $BC46
; bank08 file $011B49
$BB39: EE 01 05  ; INC ab $0501
; bank08 file $011B4C
$BB3C: 60        ; RTS i $0000
; bank08 file $011B4D
$BB3D: AD 07 05  ; LDA ab $0507
; bank08 file $011B50
$BB40: 29 0F     ; AND im $000F
; bank08 file $011B52
$BB42: 20 68 F3  ; JSR ab $F368
; bank08 file $011B55
$BB45: A0 03     ; LDY im $0003
; bank08 file $011B57
$BB47: B1 00     ; LDA iy $0000
; bank08 file $011B59
$BB49: C9 03     ; CMP im $0003
; bank08 file $011B5B
$BB4B: F0 28     ; BEQ rel $0028
; bank08 file $011B5D
$BB4D: 8D 44 6F  ; STA ab $6F44
; bank08 file $011B60
$BB50: AD 14 05  ; LDA ab $0514
; bank08 file $011B63
$BB53: D0 10     ; BNE rel $0010
; bank08 file $011B65
$BB55: A9 0D     ; LDA im $000D
; bank08 file $011B67
$BB57: 8D 00 05  ; STA ab $0500
; bank08 file $011B6A
$BB5A: A9 00     ; LDA im $0000
; bank08 file $011B6C
$BB5C: 8D 01 05  ; STA ab $0501
; bank08 file $011B6F
$BB5F: A9 02     ; LDA im $0002
; bank08 file $011B71
$BB61: 8D 0B 05  ; STA ab $050B
; bank08 file $011B74
$BB64: 60        ; RTS i $0000
; bank08 file $011B75
$BB65: A9 0E     ; LDA im $000E
; bank08 file $011B77
$BB67: 8D 00 05  ; STA ab $0500
; bank08 file $011B7A
$BB6A: A9 00     ; LDA im $0000
; bank08 file $011B7C
$BB6C: 8D 01 05  ; STA ab $0501
; bank08 file $011B7F
$BB6F: A9 02     ; LDA im $0002
; bank08 file $011B81
$BB71: 8D 0B 05  ; STA ab $050B
; bank08 file $011B84
$BB74: 60        ; RTS i $0000
; bank08 file $011B85
$BB75: A9 00     ; LDA im $0000
; bank08 file $011B87
$BB77: 8D 04 05  ; STA ab $0504
; bank08 file $011B8A
$BB7A: AD 14 05  ; LDA ab $0514
; bank08 file $011B8D
$BB7D: D0 08     ; BNE rel $0008
; bank08 file $011B8F
$BB7F: A9 01     ; LDA im $0001
; bank08 file $011B91
$BB81: 8D 91 6F  ; STA ab $6F91
; bank08 file $011B94
$BB84: 4C 8C BB  ; JMP ab $BB8C
; bank08 file $011B97
$BB87: A9 00     ; LDA im $0000
; bank08 file $011B99
$BB89: 8D 91 6F  ; STA ab $6F91
; bank08 file $011B9C
$BB8C: 20 46 BC  ; JSR ab $BC46
; bank08 file $011B9F
$BB8F: EE 01 05  ; INC ab $0501
; bank08 file $011BA2
$BB92: 60        ; RTS i $0000
; bank08 file $011BA3
$BB93: 20 EE EC  ; JSR ab $ECEE
; bank08 file $011BA6
$BB96: 20 0A BF  ; JSR ab $BF0A
; bank08 file $011BA9
$BB99: 20 27 C0  ; JSR ab $C027
; bank08 file $011BAC
$BB9C: EE 01 05  ; INC ab $0501
; bank08 file $011BAF
$BB9F: 60        ; RTS i $0000
; bank08 file $011BB0
$BBA0: AD 87 00  ; LDA ab $0087
; bank08 file $011BB3
$BBA3: 10 12     ; BPL rel $0012
; bank08 file $011BB5
$BBA5: 20 B8 BB  ; JSR ab $BBB8
; bank08 file $011BB8
$BBA8: A9 01     ; LDA im $0001
; bank08 file $011BBA
$BBAA: 8D 7A 00  ; STA ab $007A
; bank08 file $011BBD
$BBAD: A9 0D     ; LDA im $000D
; bank08 file $011BBF
$BBAF: 8D 00 04  ; STA ab $0400
; bank08 file $011BC2
$BBB2: A9 00     ; LDA im $0000
; bank08 file $011BC4
$BBB4: 8D 01 04  ; STA ab $0401
; bank08 file $011BC7
$BBB7: 60        ; RTS i $0000
; bank08 file $011F1A
$BF0A: AD 14 05  ; LDA ab $0514
; bank08 file $011F1D
$BF0D: F0 01     ; BEQ rel $0001
; bank08 file $011F1F
$BF0F: 60        ; RTS i $0000
; bank08 file $011F20
$BF10: A0 30     ; LDY im $0030
; bank08 file $011F22
$BF12: 20 5F F2  ; JSR ab $F25F
; bank08 file $011F25
$BF15: AD 0E 05  ; LDA ab $050E
; bank08 file $011F28
$BF18: 20 AF F2  ; JSR ab $F2AF
; bank08 file $011F2B
$BF1B: AD 00 00  ; LDA ab $0000
; bank08 file $011F2E
$BF1E: 8D 1A 00  ; STA ab $001A
; bank08 file $011F31
$BF21: AD 01 00  ; LDA ab $0001
; bank08 file $011F34
$BF24: 8D 1B 00  ; STA ab $001B
; bank08 file $011F37
$BF27: 20 7A E8  ; JSR ab $E87A
; bank08 file $011F3A
$BF2A: 29 01     ; AND im $0001
; bank08 file $011F3C
$BF2C: 18        ; CLC i $0000
; bank08 file $011F3D
$BF2D: 69 01     ; ADC im $0001
; bank08 file $011F3F
$BF2F: 8D 03 00  ; STA ab $0003
; bank08 file $011F42
$BF32: A0 06     ; LDY im $0006
; bank08 file $011F44
$BF34: 20 9E BF  ; JSR ab $BF9E
; bank08 file $011F47
$BF37: A2 00     ; LDX im $0000
; bank08 file $011F49
$BF39: AD 06 05  ; LDA ab $0506
; bank08 file $011F4C
$BF3C: C9 06     ; CMP im $0006
; bank08 file $011F4E
$BF3E: 90 10     ; BCC rel $0010
; bank08 file $011F50
$BF40: E8        ; INX i $0000
; bank08 file $011F51
$BF41: C9 0B     ; CMP im $000B
; bank08 file $011F53
$BF43: 90 0B     ; BCC rel $000B
; bank08 file $011F55
$BF45: E8        ; INX i $0000
; bank08 file $011F56
$BF46: C9 10     ; CMP im $0010
; bank08 file $011F58
$BF48: 90 06     ; BCC rel $0006
; bank08 file $011F5A
$BF4A: E8        ; INX i $0000
; bank08 file $011F5B
$BF4B: C9 15     ; CMP im $0015
; bank08 file $011F5D
$BF4D: 90 01     ; BCC rel $0001
; bank08 file $011F5F
$BF4F: E8        ; INX i $0000
; bank08 file $011F60
$BF50: BD 15 C0  ; LDA abx $C015
; bank08 file $011F63
$BF53: 8D 10 00  ; STA ab $0010
; bank08 file $011F66
$BF56: AD 10 00  ; LDA ab $0010
; bank08 file $011F69
$BF59: 8D 03 00  ; STA ab $0003
; bank08 file $011F6C
$BF5C: A0 08     ; LDY im $0008
; bank08 file $011F6E
$BF5E: 20 9E BF  ; JSR ab $BF9E
; bank08 file $011F71
$BF61: AD 10 00  ; LDA ab $0010
; bank08 file $011F74
$BF64: 8D 03 00  ; STA ab $0003
; bank08 file $011F77
$BF67: A0 0E     ; LDY im $000E
; bank08 file $011F79
$BF69: 20 9E BF  ; JSR ab $BF9E
; bank08 file $011F7C
$BF6C: AD 10 00  ; LDA ab $0010
; bank08 file $011F7F
$BF6F: 8D 03 00  ; STA ab $0003
; bank08 file $011F82
$BF72: A0 0B     ; LDY im $000B
; bank08 file $011F84
$BF74: B1 1A     ; LDA iy $001A
; bank08 file $011F86
$BF76: 8D 00 00  ; STA ab $0000
; bank08 file $011F89
$BF79: A9 00     ; LDA im $0000
; bank08 file $011F8B
$BF7B: 8D 01 00  ; STA ab $0001
; bank08 file $011F8E
$BF7E: 8D 02 00  ; STA ab $0002
; bank08 file $011F91
$BF81: 20 B3 BF  ; JSR ab $BFB3
; bank08 file $011F94
$BF84: A0 02     ; LDY im $0002
; bank08 file $011F96
$BF86: 20 EC BF  ; JSR ab $BFEC
; bank08 file $011F99
$BF89: 8D 03 00  ; STA ab $0003
; bank08 file $011F9C
$BF8C: A0 02     ; LDY im $0002
; bank08 file $011F9E
$BF8E: 20 9E BF  ; JSR ab $BF9E
; bank08 file $011FA1
$BF91: A0 04     ; LDY im $0004
; bank08 file $011FA3
$BF93: 20 EC BF  ; JSR ab $BFEC
; bank08 file $011FA6
$BF96: 8D 03 00  ; STA ab $0003
; bank08 file $011FA9
$BF99: A0 04     ; LDY im $0004
; bank08 file $011FAB
$BF9B: 4C 9E BF  ; JMP ab $BF9E
; bank08 file $011FAE
$BF9E: 98        ; TYA i $0000
; bank08 file $011FAF
$BF9F: 48        ; PHA i $0000
; bank08 file $011FB0
$BFA0: B1 1A     ; LDA iy $001A
; bank08 file $011FB2
$BFA2: 8D 00 00  ; STA ab $0000
; bank08 file $011FB5
$BFA5: C8        ; INY i $0000
; bank08 file $011FB6
$BFA6: B1 1A     ; LDA iy $001A
; bank08 file $011FB8
$BFA8: 8D 01 00  ; STA ab $0001
; bank08 file $011FBB
$BFAB: A9 00     ; LDA im $0000
; bank08 file $011FBD
$BFAD: 8D 02 00  ; STA ab $0002
; bank08 file $011FC0
$BFB0: 4C B5 BF  ; JMP ab $BFB5
; bank08 file $011FC3
$BFB3: 98        ; TYA i $0000
; bank08 file $011FC4
$BFB4: 48        ; PHA i $0000
; bank08 file $011FC5
$BFB5: A9 0A     ; LDA im $000A
; bank08 file $011FC7
$BFB7: 38        ; SEC i $0000
; bank08 file $011FC8
$BFB8: ED 03 00  ; SBC ab $0003
; bank08 file $011FCB
$BFBB: 8D 03 00  ; STA ab $0003
; bank08 file $011FCE
$BFBE: 20 E9 EB  ; JSR ab $EBE9
; bank08 file $011FD1
$BFC1: AD 06 00  ; LDA ab $0006
; bank08 file $011FD4
$BFC4: 8D 01 00  ; STA ab $0001
; bank08 file $011FD7
$BFC7: AD 07 00  ; LDA ab $0007
; bank08 file $011FDA
$BFCA: 8D 02 00  ; STA ab $0002
; bank08 file $011FDD
$BFCD: A9 0A     ; LDA im $000A
; bank08 file $011FDF
$BFCF: 8D 03 00  ; STA ab $0003
; bank08 file $011FE2
$BFD2: A9 00     ; LDA im $0000
; bank08 file $011FE4
$BFD4: 8D 04 00  ; STA ab $0004
; bank08 file $011FE7
$BFD7: 20 7C EA  ; JSR ab $EA7C
; bank08 file $011FEA
$BFDA: 68        ; PLA i $0000
; bank08 file $011FEB
$BFDB: A8        ; TAY i $0000
; bank08 file $011FEC
$BFDC: AD 01 00  ; LDA ab $0001
; bank08 file $011FEF
$BFDF: 91 1A     ; STA iy $001A
; bank08 file $011FF1
$BFE1: C0 0B     ; CPY im $000B
; bank08 file $011FF3
$BFE3: F0 06     ; BEQ rel $0006
; bank08 file $011FF5
$BFE5: C8        ; INY i $0000
; bank08 file $011FF6
$BFE6: AD 02 00  ; LDA ab $0002
; bank08 file $011FF9
$BFE9: 91 1A     ; STA iy $001A
; bank08 file $011FFB
$BFEB: 60        ; RTS i $0000
; bank08 file $011FFC
$BFEC: B1 1A     ; LDA iy $001A
; bank08 file $011FFE
$BFEE: 8D 00 00  ; STA ab $0000
; bank08 file $012001
$BFF1: C8        ; INY i $0000
; bank08 file $012002
$BFF2: B1 1A     ; LDA iy $001A
; bank08 file $012004
$BFF4: 8D 01 00  ; STA ab $0001
; bank08 file $012007
$BFF7: A2 00     ; LDX im $0000
; bank08 file $012009
$BFF9: BD 1A C0  ; LDA abx $C01A
; bank08 file $01200C
$BFFC: 38        ; SEC i $0000
; bank08 file $01200D
$BFFD: ED 00 00  ; SBC ab $0000
; bank09 file $012010
$C000: BD 1B C0  ; LDA abx $C01B
; bank09 file $012013
$C003: ED 01 00  ; SBC ab $0001
; bank09 file $012016
$C006: 90 06     ; BCC rel $0006
; bank09 file $012018
$C008: E8        ; INX i $0000
; bank09 file $012019
$C009: E8        ; INX i $0000
; bank09 file $01201A
$C00A: E0 08     ; CPX im $0008
; bank09 file $01201C
$C00C: 90 EB     ; BCC rel $00EB
; bank09 file $01201E
$C00E: 8A        ; TXA i $0000
; bank09 file $01201F
$C00F: 4A        ; LSR a $0000
; bank09 file $012020
$C010: AA        ; TAX i $0000
; bank09 file $012021
$C011: BD 22 C0  ; LDA abx $C022
; bank09 file $012024
$C014: 60        ; RTS i $0000
; bank13 file $01B500
$D4F0: 20 29 CC  ; JSR ab $CC29
; bank13 file $01B503
$D4F3: A0 28     ; LDY im $0028
; bank13 file $01B505
$D4F5: 20 07 EE  ; JSR ab $EE07
; bank13 file $01B50A
$D4FA: 60        ; RTS i $0000
; bank31 file $03F26F
$F25F: 8C E1 00  ; STY ab $00E1
; bank31 file $03F272
$F262: 8C 00 E0  ; STY ab $E000
; bank31 file $03F275
$F265: 60        ; RTS i $0000
; bank31 file $03F2BF
$F2AF: A0 00     ; LDY im $0000
; bank31 file $03F2C1
$F2B1: 8C 01 00  ; STY ab $0001
; bank31 file $03F2C4
$F2B4: 0A        ; ASL a $0000
; bank31 file $03F2C5
$F2B5: 2E 01 00  ; ROL ab $0001
; bank31 file $03F2C8
$F2B8: 0A        ; ASL a $0000
; bank31 file $03F2C9
$F2B9: 2E 01 00  ; ROL ab $0001
; bank31 file $03F2CC
$F2BC: 0A        ; ASL a $0000
; bank31 file $03F2CD
$F2BD: 2E 01 00  ; ROL ab $0001
; bank31 file $03F2D0
$F2C0: 0A        ; ASL a $0000
; bank31 file $03F2D1
$F2C1: 2E 01 00  ; ROL ab $0001
; bank31 file $03F2D4
$F2C4: 0A        ; ASL a $0000
; bank31 file $03F2D5
$F2C5: 2E 01 00  ; ROL ab $0001
; bank31 file $03F2D8
$F2C8: 18        ; CLC i $0000
; bank31 file $03F2D9
$F2C9: 69 00     ; ADC im $0000
; bank31 file $03F2DB
$F2CB: 8D 00 00  ; STA ab $0000
; bank31 file $03F2DE
$F2CE: AD 01 00  ; LDA ab $0001
; bank31 file $03F2E1
$F2D1: 69 60     ; ADC im $0060
; bank31 file $03F2E3
$F2D3: 8D 01 00  ; STA ab $0001
; bank31 file $03F2E6
$F2D6: 60        ; RTS i $0000
