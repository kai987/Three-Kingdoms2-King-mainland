; New29 readonly context; all offsets include16byte NES header
; bank8 file$011AC3
$BAB3: AD 01 05    ; LDA ab $0501
; bank8 file$011AC6
$BAB6: 20 DE EA    ; JSR ab $EADE
; bank8 file$011BB0
$BBA0: AD 87 00    ; LDA ab $0087
; bank8 file$011BB3
$BBA3: 10 12       ; BPL rel $0012
; bank8 file$011BB5
$BBA5: 20 B8 BB    ; JSR ab $BBB8
; bank8 file$011BB8
$BBA8: A9 01       ; LDA im $0001
; bank8 file$011BBA
$BBAA: 8D 7A 00    ; STA ab $007A
; bank8 file$011BBD
$BBAD: A9 0D       ; LDA im $000D
; bank8 file$011BBF
$BBAF: 8D 00 04    ; STA ab $0400
; bank8 file$011BC2
$BBB2: A9 00       ; LDA im $0000
; bank8 file$011BC4
$BBB4: 8D 01 04    ; STA ab $0401
; bank8 file$011BC7
$BBB7: 60          ; RTS i $0000
; bank8 file$011BC8
$BBB8: A0 30       ; LDY im $0030
; bank8 file$011BCA
$BBBA: 20 5F F2    ; JSR ab $F25F
; bank8 file$011BCD
$BBBD: AD 0E 05    ; LDA ab $050E
; bank8 file$011BD0
$BBC0: 20 AF F2    ; JSR ab $F2AF
; bank8 file$011BD3
$BBC3: AD 14 05    ; LDA ab $0514
; bank8 file$011BD6
$BBC6: D0 17       ; BNE rel $0017
; bank8 file$011BD8
$BBC8: AD 07 05    ; LDA ab $0507
; bank8 file$011BDB
$BBCB: 4A          ; LSR a $0000
; bank8 file$011BDC
$BBCC: 4A          ; LSR a $0000
; bank8 file$011BDD
$BBCD: 4A          ; LSR a $0000
; bank8 file$011BDE
$BBCE: 4A          ; LSR a $0000
; bank8 file$011BDF
$BBCF: 29 0F       ; AND im $000F
; bank8 file$011BE1
$BBD1: 8D 02 00    ; STA ab $0002
; bank8 file$011BE4
$BBD4: A0 00       ; LDY im $0000
; bank8 file$011BE6
$BBD6: B1 00       ; LDA iy $0000
; bank8 file$011BE8
$BBD8: 29 F0       ; AND im $00F0
; bank8 file$011BEA
$BBDA: 0D 02 00    ; ORA ab $0002
; bank8 file$011BED
$BBDD: 91 00       ; STA iy $0000
; bank8 file$011BEF
$BBDF: 20 00 BC    ; JSR ab $BC00
; bank8 file$011BF2
$BBE2: AD 0E 05    ; LDA ab $050E
; bank8 file$011BF5
$BBE5: 0A          ; ASL a $0000
; bank8 file$011BF6
$BBE6: 0A          ; ASL a $0000
; bank8 file$011BF7
$BBE7: 0A          ; ASL a $0000
; bank8 file$011BF8
$BBE8: A8          ; TAY i $0000
; bank8 file$011BF9
$BBE9: 98          ; TYA i $0000
; bank8 file$011BFA
$BBEA: 48          ; PHA i $0000
; bank8 file$011BFB
$BBEB: B9 72 9D    ; LDA aby $9D72
; bank8 file$011BFE
$BBEE: C9 FF       ; CMP im $00FF
; bank8 file$011C00
$BBF0: D0 02       ; BNE rel $0002
; bank8 file$011C02
$BBF2: 68          ; PLA i $0000
; bank8 file$011C03
$BBF3: 60          ; RTS i $0000
; bank8 file$011C04
$BBF4: 20 AF F2    ; JSR ab $F2AF
; bank8 file$011C07
$BBF7: 20 00 BC    ; JSR ab $BC00
; bank8 file$011C0A
$BBFA: 68          ; PLA i $0000
; bank8 file$011C0B
$BBFB: A8          ; TAY i $0000
; bank8 file$011C0C
$BBFC: C8          ; INY i $0000
; bank8 file$011C0D
$BBFD: 4C E9 BB    ; JMP ab $BBE9
; bank8 file$011C10
$BC00: AD 00 00    ; LDA ab $0000
; bank8 file$011C13
$BC03: 8D 0A 00    ; STA ab $000A
; bank8 file$011C16
$BC06: AD 01 00    ; LDA ab $0001
; bank8 file$011C19
$BC09: 8D 0B 00    ; STA ab $000B
; bank8 file$011C1C
$BC0C: A0 00       ; LDY im $0000
; bank8 file$011C1E
$BC0E: B1 0A       ; LDA iy $000A
; bank8 file$011C20
$BC10: 29 0F       ; AND im $000F
; bank8 file$011C22
$BC12: C9 07       ; CMP im $0007
; bank8 file$011C24
$BC14: D0 01       ; BNE rel $0001
; bank8 file$011C26
$BC16: 60          ; RTS i $0000
; bank8 file$011C27
$BC17: 20 68 F3    ; JSR ab $F368
; bank8 file$011C2A
$BC1A: A0 00       ; LDY im $0000
; bank8 file$011C2C
$BC1C: B1 00       ; LDA iy $0000
; bank8 file$011C2E
$BC1E: 8D 02 00    ; STA ab $0002
; bank8 file$011C31
$BC21: A0 11       ; LDY im $0011
; bank8 file$011C33
$BC23: B1 0A       ; LDA iy $000A
; bank8 file$011C35
$BC25: CD 02 00    ; CMP ab $0002
; bank8 file$011C38
$BC28: F0 06       ; BEQ rel $0006
; bank8 file$011C3A
$BC2A: C8          ; INY i $0000
; bank8 file$011C3B
$BC2B: C0 1B       ; CPY im $001B
; bank8 file$011C3D
$BC2D: 90 F4       ; BCC rel $00F4
; bank8 file$011C3F
$BC2F: 60          ; RTS i $0000
; bank8 file$011C40
$BC30: 98          ; TYA i $0000
; bank8 file$011C41
$BC31: 48          ; PHA i $0000
; bank8 file$011C42
$BC32: A0 11       ; LDY im $0011
; bank8 file$011C44
$BC34: B1 0A       ; LDA iy $000A
; bank8 file$011C46
$BC36: 8D 03 00    ; STA ab $0003
; bank8 file$011C49
$BC39: AD 02 00    ; LDA ab $0002
; bank8 file$011C4C
$BC3C: 91 0A       ; STA iy $000A
; bank8 file$011C4E
$BC3E: 68          ; PLA i $0000
; bank8 file$011C4F
$BC3F: A8          ; TAY i $0000
; bank8 file$011C50
$BC40: AD 03 00    ; LDA ab $0003
; bank8 file$011C53
$BC43: 91 0A       ; STA iy $000A
; bank8 file$011C55
$BC45: 60          ; RTS i $0000
; bank13 file$01AC39
$CC29: A0 31       ; LDY im $0031
; bank13 file$01AC3B
$CC2B: 20 5F F2    ; JSR ab $F25F
; bank13 file$01AC3E
$CC2E: A9 00       ; LDA im $0000
; bank13 file$01AC40
$CC30: 85 0A       ; STA zp $000A
; bank13 file$01AC42
$CC32: AD 5E 00    ; LDA ab $005E
; bank13 file$01AC45
$CC35: 29 01       ; AND im $0001
; bank13 file$01AC47
$CC37: D0 06       ; BNE rel $0006
; bank13 file$01AC49
$CC39: 20 45 CC    ; JSR ab $CC45
; bank13 file$01AC4C
$CC3C: 4C 5A CC    ; JMP ab $CC5A
; bank13 file$01AC4F
$CC3F: 20 5A CC    ; JSR ab $CC5A
; bank13 file$01AC52
$CC42: 4C 45 CC    ; JMP ab $CC45
; bank13 file$01AC55
$CC45: A9 40       ; LDA im $0040
; bank13 file$01AC57
$CC47: 85 0B       ; STA zp $000B
; bank13 file$01AC59
$CC49: A9 00       ; LDA im $0000
; bank13 file$01AC5B
$CC4B: 85 0C       ; STA zp $000C
; bank13 file$01AC5D
$CC4D: AD 07 05    ; LDA ab $0507
; bank13 file$01AC60
$CC50: 4A          ; LSR a $0000
; bank13 file$01AC61
$CC51: 4A          ; LSR a $0000
; bank13 file$01AC62
$CC52: 4A          ; LSR a $0000
; bank13 file$01AC63
$CC53: 4A          ; LSR a $0000
; bank13 file$01AC64
$CC54: 20 6D CC    ; JSR ab $CC6D
; bank13 file$01AC67
$CC57: 85 AF       ; STA zp $00AF
; bank13 file$01AC69
$CC59: 60          ; RTS i $0000
; bank13 file$01AC6A
$CC5A: A9 80       ; LDA im $0080
; bank13 file$01AC6C
$CC5C: 85 0B       ; STA zp $000B
; bank13 file$01AC6E
$CC5E: A9 70       ; LDA im $0070
; bank13 file$01AC70
$CC60: 85 0C       ; STA zp $000C
; bank13 file$01AC72
$CC62: AD 07 05    ; LDA ab $0507
; bank13 file$01AC75
$CC65: 29 0F       ; AND im $000F
; bank13 file$01AC77
$CC67: 20 6D CC    ; JSR ab $CC6D
; bank13 file$01AC7A
$CC6A: 85 B0       ; STA zp $00B0
; bank13 file$01AC7C
$CC6C: 60          ; RTS i $0000
; bank13 file$01AC7D
$CC6D: 20 68 F3    ; JSR ab $F368
; bank13 file$01AC80
$CC70: A0 00       ; LDY im $0000
; bank13 file$01AC82
$CC72: B1 00       ; LDA iy $0000
; bank13 file$01AC84
$CC74: 85 00       ; STA zp $0000
; bank13 file$01AC86
$CC76: A9 00       ; LDA im $0000
; bank13 file$01AC88
$CC78: 85 01       ; STA zp $0001
; bank13 file$01AC8A
$CC7A: 85 02       ; STA zp $0002
; bank13 file$01AC8C
$CC7C: A9 0D       ; LDA im $000D
; bank13 file$01AC8E
$CC7E: 85 03       ; STA zp $0003
; bank13 file$01AC90
$CC80: 20 E9 EB    ; JSR ab $EBE9
; bank13 file$01AC93
$CC83: A5 06       ; LDA zp $0006
; bank13 file$01AC95
$CC85: 18          ; CLC i $0000
; bank13 file$01AC96
$CC86: 69 B4       ; ADC im $00B4
; bank13 file$01AC98
$CC88: 85 06       ; STA zp $0006
; bank13 file$01AC9A
$CC8A: A5 07       ; LDA zp $0007
; bank13 file$01AC9C
$CC8C: 69 8D       ; ADC im $008D
; bank13 file$01AC9E
$CC8E: 85 07       ; STA zp $0007
; bank13 file$01ACA0
$CC90: A0 00       ; LDY im $0000
; bank13 file$01ACA2
$CC92: B1 06       ; LDA iy $0006
; bank13 file$01ACA4
$CC94: 48          ; PHA i $0000
; bank13 file$01ACA5
$CC95: 20 DF CC    ; JSR ab $CCDF
; bank13 file$01ACA8
$CC98: A9 00       ; LDA im $0000
; bank13 file$01ACAA
$CC9A: 48          ; PHA i $0000
; bank13 file$01ACAB
$CC9B: 20 AA CC    ; JSR ab $CCAA
; bank13 file$01ACAE
$CC9E: 68          ; PLA i $0000
; bank13 file$01ACAF
$CC9F: E6 0A       ; INC zp $000A
; bank13 file$01ACB1
$CCA1: 18          ; CLC i $0000
; bank13 file$01ACB2
$CCA2: 69 01       ; ADC im $0001
; bank13 file$01ACB4
$CCA4: C9 0C       ; CMP im $000C
; bank13 file$01ACB6
$CCA6: 90 F2       ; BCC rel $00F2
; bank13 file$01ACB8
$CCA8: 68          ; PLA i $0000
; bank13 file$01ACB9
$CCA9: 60          ; RTS i $0000
; bank13 file$01ACBA
$CCAA: A0 00       ; LDY im $0000
; bank13 file$01ACBC
$CCAC: B1 06       ; LDA iy $0006
; bank13 file$01ACBE
$CCAE: 20 DF CC    ; JSR ab $CCDF
; bank13 file$01ACC1
$CCB1: C9 FF       ; CMP im $00FF
; bank13 file$01ACC3
$CCB3: F0 29       ; BEQ rel $0029
; bank13 file$01ACC5
$CCB5: A4 0A       ; LDY zp $000A
; bank13 file$01ACC7
$CCB7: AE 7C 00    ; LDX ab $007C
; bank13 file$01ACCA
$CCBA: 18          ; CLC i $0000
; bank13 file$01ACCB
$CCBB: 65 0B       ; ADC zp $000B
; bank13 file$01ACCD
$CCBD: 9D 01 02    ; STA abx $0201
; bank13 file$01ACD0
$CCC0: B9 E6 CC    ; LDA aby $CCE6
; bank13 file$01ACD3
$CCC3: 38          ; SEC i $0000
; bank13 file$01ACD4
$CCC4: E9 01       ; SBC im $0001
; bank13 file$01ACD6
$CCC6: 9D 00 02    ; STA abx $0200
; bank13 file$01ACD9
$CCC9: B9 FE CC    ; LDA aby $CCFE
; bank13 file$01ACDC
$CCCC: 18          ; CLC i $0000
; bank13 file$01ACDD
$CCCD: 65 0C       ; ADC zp $000C
; bank13 file$01ACDF
$CCCF: 9D 03 02    ; STA abx $0203
; bank13 file$01ACE2
$CCD2: A9 00       ; LDA im $0000
; bank13 file$01ACE4
$CCD4: 9D 02 02    ; STA abx $0202
; bank13 file$01ACE7
$CCD7: E8          ; INX i $0000
; bank13 file$01ACE8
$CCD8: E8          ; INX i $0000
; bank13 file$01ACE9
$CCD9: E8          ; INX i $0000
; bank13 file$01ACEA
$CCDA: E8          ; INX i $0000
; bank13 file$01ACEB
$CCDB: 8E 7C 00    ; STX ab $007C
; bank13 file$01ACEE
$CCDE: 60          ; RTS i $0000
; bank13 file$01ACEF
$CCDF: E6 06       ; INC zp $0006
; bank13 file$01ACF1
$CCE1: D0 02       ; BNE rel $0002
; bank13 file$01ACF3
$CCE3: E6 07       ; INC zp $0007
; bank13 file$01ACF5
$CCE5: 60          ; RTS i $0000
; bank13 file$01B500
$D4F0: 20 29 CC    ; JSR ab $CC29
; bank13 file$01B503
$D4F3: A0 28       ; LDY im $0028
; bank13 file$01B505
$D4F5: 20 07 EE    ; JSR ab $EE07
; bank13 file$01B50A
$D4FA: 60          ; RTS i $0000
; bank31 file$03EBF9
$EBE9: A0 07       ; LDY im $0007
; bank31 file$03EBFB
$EBEB: A9 00       ; LDA im $0000
; bank31 file$03EBFD
$EBED: 85 04       ; STA zp $0004
; bank31 file$03EBFF
$EBEF: 85 05       ; STA zp $0005
; bank31 file$03EC01
$EBF1: 85 06       ; STA zp $0006
; bank31 file$03EC03
$EBF3: 85 07       ; STA zp $0007
; bank31 file$03EC05
$EBF5: 85 08       ; STA zp $0008
; bank31 file$03EC07
$EBF7: 85 09       ; STA zp $0009
; bank31 file$03EC09
$EBF9: 46 03       ; LSR zp $0003
; bank31 file$03EC0B
$EBFB: 90 19       ; BCC rel $0019
; bank31 file$03EC0D
$EBFD: A5 00       ; LDA zp $0000
; bank31 file$03EC0F
$EBFF: 18          ; CLC i $0000
; bank31 file$03EC10
$EC00: 65 06       ; ADC zp $0006
; bank31 file$03EC12
$EC02: 85 06       ; STA zp $0006
; bank31 file$03EC14
$EC04: A5 01       ; LDA zp $0001
; bank31 file$03EC16
$EC06: 65 07       ; ADC zp $0007
; bank31 file$03EC18
$EC08: 85 07       ; STA zp $0007
; bank31 file$03EC1A
$EC0A: A5 02       ; LDA zp $0002
; bank31 file$03EC1C
$EC0C: 65 08       ; ADC zp $0008
; bank31 file$03EC1E
$EC0E: 85 08       ; STA zp $0008
; bank31 file$03EC20
$EC10: A5 04       ; LDA zp $0004
; bank31 file$03EC22
$EC12: 65 09       ; ADC zp $0009
; bank31 file$03EC24
$EC14: 85 09       ; STA zp $0009
; bank31 file$03EC26
$EC16: 06 00       ; ASL zp $0000
; bank31 file$03EC28
$EC18: 26 01       ; ROL zp $0001
; bank31 file$03EC2A
$EC1A: 26 02       ; ROL zp $0002
; bank31 file$03EC2C
$EC1C: 26 04       ; ROL zp $0004
; bank31 file$03EC2E
$EC1E: 88          ; DEY i $0000
; bank31 file$03EC2F
$EC1F: 10 D8       ; BPL rel $00D8
; bank31 file$03EC31
$EC21: 60          ; RTS i $0000
; bank31 file$03F2BF
$F2AF: A0 00       ; LDY im $0000
; bank31 file$03F2C1
$F2B1: 8C 01 00    ; STY ab $0001
; bank31 file$03F2C4
$F2B4: 0A          ; ASL a $0000
; bank31 file$03F2C5
$F2B5: 2E 01 00    ; ROL ab $0001
; bank31 file$03F2C8
$F2B8: 0A          ; ASL a $0000
; bank31 file$03F2C9
$F2B9: 2E 01 00    ; ROL ab $0001
; bank31 file$03F2CC
$F2BC: 0A          ; ASL a $0000
; bank31 file$03F2CD
$F2BD: 2E 01 00    ; ROL ab $0001
; bank31 file$03F2D0
$F2C0: 0A          ; ASL a $0000
; bank31 file$03F2D1
$F2C1: 2E 01 00    ; ROL ab $0001
; bank31 file$03F2D4
$F2C4: 0A          ; ASL a $0000
; bank31 file$03F2D5
$F2C5: 2E 01 00    ; ROL ab $0001
; bank31 file$03F2D8
$F2C8: 18          ; CLC i $0000
; bank31 file$03F2D9
$F2C9: 69 00       ; ADC im $0000
; bank31 file$03F2DB
$F2CB: 8D 00 00    ; STA ab $0000
; bank31 file$03F2DE
$F2CE: AD 01 00    ; LDA ab $0001
; bank31 file$03F2E1
$F2D1: 69 60       ; ADC im $0060
; bank31 file$03F2E3
$F2D3: 8D 01 00    ; STA ab $0001
; bank31 file$03F2E6
$F2D6: 60          ; RTS i $0000
; bank31 file$03F378
$F368: 29 0F       ; AND im $000F
; bank31 file$03F37A
$F36A: 0A          ; ASL a $0000
; bank31 file$03F37B
$F36B: A8          ; TAY i $0000
; bank31 file$03F37C
$F36C: B9 79 F3    ; LDA aby $F379
; bank31 file$03F37F
$F36F: 8D 00 00    ; STA ab $0000
; bank31 file$03F382
$F372: B9 7A F3    ; LDA aby $F37A
; bank31 file$03F385
$F375: 8D 01 00    ; STA ab $0001
; bank31 file$03F388
$F378: 60          ; RTS i $0000

; Explicit original data
; bank8 CPU$BAB9 file$011AC9 fourstage inline table
.byte C1 BA 3D BB 93 BB A0 BB
; bank13 CPU$D4F8 file$01B508 EE07 inline A006
.byte 06 A0
; bank16 CPU$9D72 file$021D82 30x8 city adjacency
.byte 01 03 FF FF FF FF FF FF 00 02 04 03 FF FF FF FF 01 04 05 08 FF FF FF FF 00 01 04 0A FF FF FF FF 02 0C 0B 03 01 FF FF FF 07 08 02 FF FF FF FF FF 07 09 FF FF FF FF FF FF 06 09 19 08 05 FF FF FF 05 07 19 0D 0C 02 FF FF 1A 19 07 06 FF FF FF FF 03 0B 10 0F FF FF FF FF 04 0C 0E 10 0A FF FF FF 08 0D 15 0E 0B 04 FF FF 08 16 15 0C FF FF FF FF 0C 15 14 10 0B FF FF FF 0A 10 11 FF FF FF FF FF 0B 0E 14 11 0F 0A FF FF 0F 10 14 12 FF FF FF FF 11 17 14 FF FF FF FF FF 18 16 1C FF FF FF FF FF 15 17 12 11 10 0E FF FF 16 18 17 14 0E 0C 0D FF 1B 13 18 15 0D FF FF FF 15 18 12 14 FF FF FF FF 16 13 17 15 FF FF FF FF 09 1A 1B 08 07 FF FF FF 1D 1C 1B 19 09 FF FF FF 19 1A 1C 16 FF FF FF FF 1A 1D 13 1B FF FF FF FF 1A 1C FF FF FF FF FF FF
; bank31 CPU$F379 file$03F389 raw16 ruler pointer words; only first7 are ruler entries
.byte 07 6F 0F 6F 17 6F 1F 6F 27 6F 2F 6F 37 6F A0 31 20 5F F2 A0 00 8C 01 00 8D 00 00 0A 2E 01 00 18
; bank13 CPU$CCE6 file$01ACF6 24 sprite Y positions and24 X positions
.byte 10 10 18 18 10 10 18 18 10 10 18 18 10 10 18 18 10 10 18 18 10 10 18 18 28 30 28 30 38 40 38 40 48 50 48 50 28 30 28 30 38 40 38 40 48 50 48 50
