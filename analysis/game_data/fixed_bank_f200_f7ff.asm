03F210  b31:$F200  BB        .byte $BB
03F211  b31:$F201  A2 FF     LDX  #$FF
03F213  b31:$F203  4C C0 F1  JMP  $F1C0
03F216  b31:$F206  AD AE 00  LDA  $00AE
03F219  b31:$F209  8D 00 80  STA  $8000
03F21C  b31:$F20C  AD AF 00  LDA  $00AF
03F21F  b31:$F20F  8D 00 88  STA  $8800
03F222  b31:$F212  AD B0 00  LDA  $00B0
03F225  b31:$F215  8D 00 90  STA  $9000
03F228  b31:$F218  AD B1 00  LDA  $00B1
03F22B  b31:$F21B  8D 00 98  STA  $9800
03F22E  b31:$F21E  AD B2 00  LDA  $00B2
03F231  b31:$F221  8D 00 A0  STA  $A000
03F234  b31:$F224  AD B3 00  LDA  $00B3
03F237  b31:$F227  8D 00 A8  STA  $A800
03F23A  b31:$F22A  AD B4 00  LDA  $00B4
03F23D  b31:$F22D  8D 00 B0  STA  $B000
03F240  b31:$F230  AD B5 00  LDA  $00B5
03F243  b31:$F233  8D 00 B8  STA  $B800
03F246  b31:$F236  60        RTS
03F247  b31:$F237  8C E2 00  STY  $00E2
03F24A  b31:$F23A  C8        INY
03F24B  b31:$F23B  8C E3 00  STY  $00E3
03F24E  b31:$F23E  8C 00 F0  STY  $F000
03F251  b31:$F241  88        DEY
03F252  b31:$F242  48        PHA
03F253  b31:$F243  98        TYA
03F254  b31:$F244  09 C0     ORA  #$C0
03F256  b31:$F246  8D 00 E8  STA  $E800
03F259  b31:$F249  68        PLA
03F25A  b31:$F24A  60        RTS
03F25B  b31:$F24B  8C DF 00  STY  $00DF
03F25E  b31:$F24E  C8        INY
03F25F  b31:$F24F  8C E0 00  STY  $00E0
03F262  b31:$F252  8C 00 F0  STY  $F000
03F265  b31:$F255  88        DEY
03F266  b31:$F256  48        PHA
03F267  b31:$F257  98        TYA
03F268  b31:$F258  09 C0     ORA  #$C0
03F26A  b31:$F25A  8D 00 E8  STA  $E800
03F26D  b31:$F25D  68        PLA
03F26E  b31:$F25E  60        RTS
03F26F  b31:$F25F  8C E1 00  STY  $00E1
03F272  b31:$F262  8C 00 E0  STY  $E000
03F275  b31:$F265  60        RTS
03F276  b31:$F266  8C DE 00  STY  $00DE
03F279  b31:$F269  8C 00 E0  STY  $E000
03F27C  b31:$F26C  60        RTS
03F27D  b31:$F26D  8D 11 03  STA  $0311
03F280  b31:$F270  A9 00     LDA  #$00
03F282  b31:$F272  8D 10 03  STA  $0310
03F285  b31:$F275  A9 FF     LDA  #$FF
03F287  b31:$F277  8D 12 03  STA  $0312
03F28A  b31:$F27A  8D 13 03  STA  $0313
03F28D  b31:$F27D  A9 00     LDA  #$00
03F28F  b31:$F27F  8D 00 03  STA  $0300
03F292  b31:$F282  60        RTS
03F293  b31:$F283  8D 11 03  STA  $0311
03F296  b31:$F286  A9 02     LDA  #$02
03F298  b31:$F288  4C 72 F2  JMP  $F272
03F29B  b31:$F28B  8D 11 03  STA  $0311
03F29E  b31:$F28E  A9 04     LDA  #$04
03F2A0  b31:$F290  4C 72 F2  JMP  $F272
03F2A3  b31:$F293  8D 11 03  STA  $0311
03F2A6  b31:$F296  A9 05     LDA  #$05
03F2A8  b31:$F298  4C 72 F2  JMP  $F272
03F2AB  b31:$F29B  8D 10 03  STA  $0310
03F2AE  b31:$F29E  A9 FF     LDA  #$FF
03F2B0  b31:$F2A0  8D 11 03  STA  $0311
03F2B3  b31:$F2A3  8D 12 03  STA  $0312
03F2B6  b31:$F2A6  8D 13 03  STA  $0313
03F2B9  b31:$F2A9  A9 00     LDA  #$00
03F2BB  b31:$F2AB  8D 00 03  STA  $0300
03F2BE  b31:$F2AE  60        RTS
03F2BF  b31:$F2AF  A0 00     LDY  #$00
03F2C1  b31:$F2B1  8C 01 00  STY  $0001
03F2C4  b31:$F2B4  0A        ASL  A
03F2C5  b31:$F2B5  2E 01 00  ROL  $0001
03F2C8  b31:$F2B8  0A        ASL  A
03F2C9  b31:$F2B9  2E 01 00  ROL  $0001
03F2CC  b31:$F2BC  0A        ASL  A
03F2CD  b31:$F2BD  2E 01 00  ROL  $0001
03F2D0  b31:$F2C0  0A        ASL  A
03F2D1  b31:$F2C1  2E 01 00  ROL  $0001
03F2D4  b31:$F2C4  0A        ASL  A
03F2D5  b31:$F2C5  2E 01 00  ROL  $0001
03F2D8  b31:$F2C8  18        CLC
03F2D9  b31:$F2C9  69 00     ADC  #$00
03F2DB  b31:$F2CB  8D 00 00  STA  $0000
03F2DE  b31:$F2CE  AD 01 00  LDA  $0001
03F2E1  b31:$F2D1  69 60     ADC  #$60
03F2E3  b31:$F2D3  8D 01 00  STA  $0001
03F2E6  b31:$F2D6  60        RTS
03F2E7  b31:$F2D7  A0 00     LDY  #$00
03F2E9  b31:$F2D9  8C 01 00  STY  $0001
03F2EC  b31:$F2DC  8D 00 00  STA  $0000
03F2EF  b31:$F2DF  0A        ASL  A
03F2F0  b31:$F2E0  2E 01 00  ROL  $0001
03F2F3  b31:$F2E3  18        CLC
03F2F4  b31:$F2E4  6D 00 00  ADC  $0000
03F2F7  b31:$F2E7  48        PHA
03F2F8  b31:$F2E8  AD 01 00  LDA  $0001
03F2FB  b31:$F2EB  69 00     ADC  #$00
03F2FD  b31:$F2ED  8D 01 00  STA  $0001
03F300  b31:$F2F0  68        PLA
03F301  b31:$F2F1  0A        ASL  A
03F302  b31:$F2F2  2E 01 00  ROL  $0001
03F305  b31:$F2F5  0A        ASL  A
03F306  b31:$F2F6  2E 01 00  ROL  $0001
03F309  b31:$F2F9  18        CLC
03F30A  b31:$F2FA  69 C0     ADC  #$C0
03F30C  b31:$F2FC  8D 00 00  STA  $0000
03F30F  b31:$F2FF  AD 01 00  LDA  $0001
03F312  b31:$F302  69 63     ADC  #$63
03F314  b31:$F304  8D 01 00  STA  $0001
03F317  b31:$F307  60        RTS
03F318  b31:$F308  8D 02 00  STA  $0002
03F31B  b31:$F30B  A0 30     LDY  #$30
03F31D  b31:$F30D  20 5F F2  JSR  $F25F
03F320  b31:$F310  A9 00     LDA  #$00
03F322  b31:$F312  8D 01 00  STA  $0001
03F325  b31:$F315  AD 02 00  LDA  $0002
03F328  b31:$F318  0A        ASL  A
03F329  b31:$F319  2E 01 00  ROL  $0001
03F32C  b31:$F31C  0A        ASL  A
03F32D  b31:$F31D  2E 01 00  ROL  $0001
03F330  b31:$F320  18        CLC
03F331  b31:$F321  6D 02 00  ADC  $0002
03F334  b31:$F324  8D 00 00  STA  $0000
03F337  b31:$F327  AD 01 00  LDA  $0001
03F33A  b31:$F32A  69 00     ADC  #$00
03F33C  b31:$F32C  8D 01 00  STA  $0001
03F33F  b31:$F32F  0E 00 00  ASL  $0000
03F342  b31:$F332  2E 01 00  ROL  $0001
03F345  b31:$F335  AD 00 00  LDA  $0000
03F348  b31:$F338  18        CLC
03F349  b31:$F339  69 1A     ADC  #$1A
03F34B  b31:$F33B  8D 00 00  STA  $0000
03F34E  b31:$F33E  AD 01 00  LDA  $0001
03F351  b31:$F341  69 90     ADC  #$90
03F353  b31:$F343  8D 01 00  STA  $0001
03F356  b31:$F346  A0 00     LDY  #$00
03F358  b31:$F348  A2 00     LDX  #$00
03F35A  b31:$F34A  B1 00     LDA  ($00),Y
03F35C  b31:$F34C  F0 0D     BEQ  $F35B
03F35E  b31:$F34E  C8        INY
03F35F  b31:$F34F  C9 39     CMP  #$39
03F361  b31:$F351  F0 F7     BEQ  $F34A
03F363  b31:$F353  C9 3A     CMP  #$3A
03F365  b31:$F355  F0 F3     BEQ  $F34A
03F367  b31:$F357  E8        INX
03F368  b31:$F358  4C 4A F3  JMP  $F34A
03F36B  b31:$F35B  BD 5F F3  LDA  $F35F,X
03F36E  b31:$F35E  60        RTS
03F36F  b31:$F35F  03        .byte $03
03F370  b31:$F360  03        .byte $03
03F371  b31:$F361  03        .byte $03
03F372  b31:$F362  02        .byte $02
03F373  b31:$F363  02        .byte $02
03F374  b31:$F364  01 01     ORA  ($01,X)
03F376  b31:$F366  00        BRK
03F377  b31:$F367  00        BRK
03F378  b31:$F368  29 0F     AND  #$0F
03F37A  b31:$F36A  0A        ASL  A
03F37B  b31:$F36B  A8        TAY
03F37C  b31:$F36C  B9 79 F3  LDA  $F379,Y
03F37F  b31:$F36F  8D 00 00  STA  $0000
03F382  b31:$F372  B9 7A F3  LDA  $F37A,Y
03F385  b31:$F375  8D 01 00  STA  $0001
03F388  b31:$F378  60        RTS
03F389  b31:$F379  07        .byte $07
03F38A  b31:$F37A  6F        .byte $6F
03F38B  b31:$F37B  0F        .byte $0F
03F38C  b31:$F37C  6F        .byte $6F
03F38D  b31:$F37D  17        .byte $17
03F38E  b31:$F37E  6F        .byte $6F
03F38F  b31:$F37F  1F        .byte $1F
03F390  b31:$F380  6F        .byte $6F
03F391  b31:$F381  27        .byte $27
03F392  b31:$F382  6F        .byte $6F
03F393  b31:$F383  2F        .byte $2F
03F394  b31:$F384  6F        .byte $6F
03F395  b31:$F385  37        .byte $37
03F396  b31:$F386  6F        .byte $6F
03F397  b31:$F387  A0 31     LDY  #$31
03F399  b31:$F389  20 5F F2  JSR  $F25F
03F39C  b31:$F38C  A0 00     LDY  #$00
03F39E  b31:$F38E  8C 01 00  STY  $0001
03F3A1  b31:$F391  8D 00 00  STA  $0000
03F3A4  b31:$F394  0A        ASL  A
03F3A5  b31:$F395  2E 01 00  ROL  $0001
03F3A8  b31:$F398  18        CLC
03F3A9  b31:$F399  6D 00 00  ADC  $0000
03F3AC  b31:$F39C  48        PHA
03F3AD  b31:$F39D  AD 01 00  LDA  $0001
03F3B0  b31:$F3A0  69 00     ADC  #$00
03F3B2  b31:$F3A2  8D 01 00  STA  $0001
03F3B5  b31:$F3A5  68        PLA
03F3B6  b31:$F3A6  0A        ASL  A
03F3B7  b31:$F3A7  2E 01 00  ROL  $0001
03F3BA  b31:$F3AA  0A        ASL  A
03F3BB  b31:$F3AB  2E 01 00  ROL  $0001
03F3BE  b31:$F3AE  18        CLC
03F3BF  b31:$F3AF  69 00     ADC  #$00
03F3C1  b31:$F3B1  8D 00 00  STA  $0000
03F3C4  b31:$F3B4  AD 01 00  LDA  $0001
03F3C7  b31:$F3B7  69 80     ADC  #$80
03F3C9  b31:$F3B9  8D 01 00  STA  $0001
03F3CC  b31:$F3BC  60        RTS
03F3CD  b31:$F3BD  A9 00     LDA  #$00
03F3CF  b31:$F3BF  8D 00 50  STA  $5000
03F3D2  b31:$F3C2  8D 00 58  STA  $5800
03F3D5  b31:$F3C5  A9 E0     LDA  #$E0
03F3D7  b31:$F3C7  8D 00 C0  STA  $C000
03F3DA  b31:$F3CA  8D 00 D0  STA  $D000
03F3DD  b31:$F3CD  A9 E1     LDA  #$E1
03F3DF  b31:$F3CF  8D 00 C8  STA  $C800
03F3E2  b31:$F3D2  8D 00 D8  STA  $D800
03F3E5  b31:$F3D5  A2 00     LDX  #$00
03F3E7  b31:$F3D7  BD BD F3  LDA  $F3BD,X
03F3EA  b31:$F3DA  29 01     AND  #$01
03F3EC  b31:$F3DC  8D 01 00  STA  $0001
03F3EF  b31:$F3DF  8D 16 40  STA  $4016
03F3F2  b31:$F3E2  AD 17 40  LDA  $4017
03F3F5  b31:$F3E5  4A        LSR  A
03F3F6  b31:$F3E6  49 FF     EOR  #$FF
03F3F8  b31:$F3E8  29 01     AND  #$01
03F3FA  b31:$F3EA  CD 01 00  CMP  $0001
03F3FD  b31:$F3ED  D0 32     BNE  $F421
03F3FF  b31:$F3EF  E8        INX
03F400  b31:$F3F0  E0 46     CPX  #$46
03F402  b31:$F3F2  D0 E3     BNE  $F3D7
03F404  b31:$F3F4  A9 40     LDA  #$40
03F406  b31:$F3F6  8D 00 F8  STA  $F800
03F409  b31:$F3F9  A2 01     LDX  #$01
03F40B  b31:$F3FB  20 22 F4  JSR  $F422
03F40E  b31:$F3FE  F0 0C     BEQ  $F40C
03F410  b31:$F400  A2 37     LDX  #$37
03F412  b31:$F402  20 3F F4  JSR  $F43F
03F415  b31:$F405  20 22 F4  JSR  $F422
03F418  b31:$F408  F0 02     BEQ  $F40C
03F41A  b31:$F40A  A2 16     LDX  #$16
03F41C  b31:$F40C  A9 3F     LDA  #$3F
03F41E  b31:$F40E  8D 06 20  STA  $2006
03F421  b31:$F411  A0 00     LDY  #$00
03F423  b31:$F413  8C 06 20  STY  $2006
03F426  b31:$F416  8E 07 20  STX  $2007
03F429  b31:$F419  C8        INY
03F42A  b31:$F41A  C0 20     CPY  #$20
03F42C  b31:$F41C  D0 F8     BNE  $F416
03F42E  b31:$F41E  4C 1E F4  JMP  $F41E
03F431  b31:$F421  60        RTS
03F432  b31:$F422  20 58 F4  JSR  $F458
03F435  b31:$F425  B1 02     LDA  ($02),Y
03F437  b31:$F427  CD 00 00  CMP  $0000
03F43A  b31:$F42A  D0 12     BNE  $F43E
03F43C  b31:$F42C  20 68 F4  JSR  $F468
03F43F  b31:$F42F  C8        INY
03F440  b31:$F430  D0 F3     BNE  $F425
03F442  b31:$F432  EE 03 00  INC  $0003
03F445  b31:$F435  AD 03 00  LDA  $0003
03F448  b31:$F438  C9 80     CMP  #$80
03F44A  b31:$F43A  D0 E9     BNE  $F425
03F44C  b31:$F43C  A9 00     LDA  #$00
03F44E  b31:$F43E  60        RTS
03F44F  b31:$F43F  20 58 F4  JSR  $F458
03F452  b31:$F442  AD 00 00  LDA  $0000
03F455  b31:$F445  91 02     STA  ($02),Y
03F457  b31:$F447  20 68 F4  JSR  $F468
03F45A  b31:$F44A  C8        INY
03F45B  b31:$F44B  D0 F5     BNE  $F442
03F45D  b31:$F44D  EE 03 00  INC  $0003
03F460  b31:$F450  AD 03 00  LDA  $0003
03F463  b31:$F453  C9 80     CMP  #$80
03F465  b31:$F455  D0 EB     BNE  $F442
03F467  b31:$F457  60        RTS
03F468  b31:$F458  A0 00     LDY  #$00
03F46A  b31:$F45A  8C 02 00  STY  $0002
03F46D  b31:$F45D  A9 60     LDA  #$60
03F46F  b31:$F45F  8D 03 00  STA  $0003
03F472  b31:$F462  A9 AA     LDA  #$AA
03F474  b31:$F464  8D 00 00  STA  $0000
03F477  b31:$F467  60        RTS
03F478  b31:$F468  AD 00 00  LDA  $0000
03F47B  b31:$F46B  0A        ASL  A
03F47C  b31:$F46C  0A        ASL  A
03F47D  b31:$F46D  38        SEC
03F47E  b31:$F46E  6D 00 00  ADC  $0000
03F481  b31:$F471  8D 00 00  STA  $0000
03F484  b31:$F474  F0 F2     BEQ  $F468
03F486  b31:$F476  60        RTS
03F487  b31:$F477  00        BRK
03F488  b31:$F478  00        BRK
03F489  b31:$F479  00        BRK
03F48A  b31:$F47A  00        BRK
03F48B  b31:$F47B  01 01     ORA  ($01,X)
03F48D  b31:$F47D  01 01     ORA  ($01,X)
03F48F  b31:$F47F  14        .byte $14
03F490  b31:$F480  15 24     ORA  $24,X
03F492  b31:$F482  25 07     AND  $07
03F494  b31:$F484  08        PHP
03F495  b31:$F485  17        .byte $17
03F496  b31:$F486  18        CLC
03F497  b31:$F487  07        .byte $07
03F498  b31:$F488  27        .byte $27
03F499  b31:$F489  1A        .byte $1A
03F49A  b31:$F48A  25 26     AND  $26
03F49C  b31:$F48C  08        PHP
03F49D  b31:$F48D  24 1B     BIT  $1B
03F49F  b31:$F48F  12        .byte $12
03F4A0  b31:$F490  15 17     ORA  $17,X
03F4A2  b31:$F492  37        .byte $37
03F4A3  b31:$F493  14        .byte $14
03F4A4  b31:$F494  13        .byte $13
03F4A5  b31:$F495  36 18     ROL  $18,X
03F4A7  b31:$F497  07        .byte $07
03F4A8  b31:$F498  0A        ASL  A
03F4A9  b31:$F499  1A        .byte $1A
03F4AA  b31:$F49A  25 0A     AND  $0A
03F4AC  b31:$F49C  08        PHP
03F4AD  b31:$F49D  24 1B     BIT  $1B
03F4AF  b31:$F49F  12        .byte $12
03F4B0  b31:$F4A0  15 17     ORA  $17,X
03F4B2  b31:$F4A2  0A        ASL  A
03F4B3  b31:$F4A3  14        .byte $14
03F4B4  b31:$F4A4  13        .byte $13
03F4B5  b31:$F4A5  0A        ASL  A
03F4B6  b31:$F4A6  18        CLC
03F4B7  b31:$F4A7  26 0A     ROL  $0A
03F4B9  b31:$F4A9  0A        ASL  A
03F4BA  b31:$F4AA  0A        ASL  A
03F4BB  b31:$F4AB  0A        ASL  A
03F4BC  b31:$F4AC  27        .byte $27
03F4BD  b31:$F4AD  0A        ASL  A
03F4BE  b31:$F4AE  0A        ASL  A
03F4BF  b31:$F4AF  0A        ASL  A
03F4C0  b31:$F4B0  0A        ASL  A
03F4C1  b31:$F4B1  0A        ASL  A
03F4C2  b31:$F4B2  37        .byte $37
03F4C3  b31:$F4B3  0A        ASL  A
03F4C4  b31:$F4B4  0A        ASL  A
03F4C5  b31:$F4B5  36 0A     ROL  $0A,X
03F4C7  b31:$F4B7  26 27     ROL  $27
03F4C9  b31:$F4B9  0A        ASL  A
03F4CA  b31:$F4BA  0A        ASL  A
03F4CB  b31:$F4BB  0A        ASL  A
03F4CC  b31:$F4BC  0A        ASL  A
03F4CD  b31:$F4BD  36 37     ROL  $37,X
03F4CF  b31:$F4BF  0A        ASL  A
03F4D0  b31:$F4C0  27        .byte $27
03F4D1  b31:$F4C1  0A        ASL  A
03F4D2  b31:$F4C2  37        .byte $37
03F4D3  b31:$F4C3  26 0A     ROL  $0A
03F4D5  b31:$F4C5  36 0A     ROL  $0A,X
03F4D7  b31:$F4C7  26 27     ROL  $27
03F4D9  b31:$F4C9  24 25     BIT  $25
03F4DB  b31:$F4CB  14        .byte $14
03F4DC  b31:$F4CC  15 36     ORA  $36,X
03F4DE  b31:$F4CE  37        .byte $37
03F4DF  b31:$F4CF  07        .byte $07
03F4E0  b31:$F4D0  27        .byte $27
03F4E1  b31:$F4D1  17        .byte $17
03F4E2  b31:$F4D2  37        .byte $37
03F4E3  b31:$F4D3  26 08     ROL  $08
03F4E5  b31:$F4D5  36 18     ROL  $18,X
03F4E7  b31:$F4D7  0A        ASL  A
03F4E8  b31:$F4D8  0A        ASL  A
03F4E9  b31:$F4D9  24 25     BIT  $25
03F4EB  b31:$F4DB  14        .byte $14
03F4EC  b31:$F4DC  15 0A     ORA  $0A,X
03F4EE  b31:$F4DE  0A        ASL  A
03F4EF  b31:$F4DF  07        .byte $07
03F4F0  b31:$F4E0  0A        ASL  A
03F4F1  b31:$F4E1  17        .byte $17
03F4F2  b31:$F4E2  0A        ASL  A
03F4F3  b31:$F4E3  0A        ASL  A
03F4F4  b31:$F4E4  08        PHP
03F4F5  b31:$F4E5  0A        ASL  A
03F4F6  b31:$F4E6  18        CLC
03F4F7  b31:$F4E7  22        .byte $22
03F4F8  b31:$F4E8  23        .byte $23
03F4F9  b31:$F4E9  04        .byte $04
03F4FA  b31:$F4EA  05 34     ORA  $34
03F4FC  b31:$F4EC  35 32     AND  $32,X
03F4FE  b31:$F4EE  33        .byte $33
03F4FF  b31:$F4EF  22        .byte $22
03F500  b31:$F4F0  06 32     ASL  $32
03F502  b31:$F4F2  16 09     ASL  $09,X
03F504  b31:$F4F4  23        .byte $23
03F505  b31:$F4F5  19 33 0C  ORA  $0C33,Y
03F508  b31:$F4F8  0D 1C 1D  ORA  $1D1C
03F50B  b31:$F4FB  0E 0F 1E  ASL  $1E0F
03F50E  b31:$F4FE  1F        .byte $1F
03F50F  b31:$F4FF  22        .byte $22
03F510  b31:$F500  40        RTI
03F511  b31:$F501  32        .byte $32
03F512  b31:$F502  50 41     BVC  $F545
03F514  b31:$F504  42        .byte $42
03F515  b31:$F505  51 52     EOR  ($52),Y
03F517  b31:$F507  43        .byte $43
03F518  b31:$F508  44        .byte $44
03F519  b31:$F509  53        .byte $53
03F51A  b31:$F50A  54        .byte $54
03F51B  b31:$F50B  22        .byte $22
03F51C  b31:$F50C  23        .byte $23
03F51D  b31:$F50D  55 33     EOR  $33,X
03F51F  b31:$F50F  46 42     LSR  $42
03F521  b31:$F511  56 54     LSR  $54,X
03F523  b31:$F513  22        .byte $22
03F524  b31:$F514  23        .byte $23
03F525  b31:$F515  55 33     EOR  $33,X
03F527  b31:$F517  2C 2D 3C  BIT  $3C2D
03F52A  b31:$F51A  3D 2E 2F  AND  $2F2E,X
03F52D  b31:$F51D  3E 3F 20  ROL  $203F,X
03F530  b31:$F520  21 30     AND  ($30,X)
03F532  b31:$F522  31 22     AND  ($22),Y
03F534  b31:$F524  23        .byte $23
03F535  b31:$F525  45 33     EOR  $33
03F537  b31:$F527  2A        ROL  A
03F538  b31:$F528  2B        .byte $2B
03F539  b31:$F529  3A        .byte $3A
03F53A  b31:$F52A  3B        .byte $3B
03F53B  b31:$F52B  60        RTS
03F53C  b31:$F52C  63        .byte $63
03F53D  b31:$F52D  70 73     BVS  $F5A2
03F53F  b31:$F52F  22        .byte $22
03F540  b31:$F530  23        .byte $23
03F541  b31:$F531  48        PHA
03F542  b31:$F532  49 58     EOR  #$58
03F544  b31:$F534  59 32 33  EOR  $3332,Y
03F547  b31:$F537  22        .byte $22
03F548  b31:$F538  57        .byte $57
03F549  b31:$F539  32        .byte $32
03F54A  b31:$F53A  33        .byte $33
03F54B  b31:$F53B  5A        .byte $5A
03F54C  b31:$F53C  23        .byte $23
03F54D  b31:$F53D  32        .byte $32
03F54E  b31:$F53E  33        .byte $33
03F54F  b31:$F53F  22        .byte $22
03F550  b31:$F540  23        .byte $23
03F551  b31:$F541  32        .byte $32
03F552  b31:$F542  47        .byte $47
03F553  b31:$F543  22        .byte $22
03F554  b31:$F544  23        .byte $23
03F555  b31:$F545  4A        LSR  A
03F556  b31:$F546  33        .byte $33
03F557  b31:$F547  22        .byte $22
03F558  b31:$F548  4B        .byte $4B
03F559  b31:$F549  32        .byte $32
03F55A  b31:$F54A  5B        .byte $5B
03F55B  b31:$F54B  4C 23 5C  JMP  $5C23
03F55E  b31:$F54E  33        .byte $33
03F55F  b31:$F54F  60        RTS
03F560  b31:$F550  61 5D     ADC  ($5D,X)
03F562  b31:$F552  3B        .byte $3B
03F563  b31:$F553  62        .byte $62
03F564  b31:$F554  63        .byte $63
03F565  b31:$F555  3A        .byte $3A
03F566  b31:$F556  5E 4D 2B  LSR  $2B4D,X
03F569  b31:$F559  70 71     BVS  $F5CC
03F56B  b31:$F55B  22        .byte $22
03F56C  b31:$F55C  23        .byte $23
03F56D  b31:$F55D  32        .byte $32
03F56E  b31:$F55E  33        .byte $33
03F56F  b31:$F55F  60        RTS
03F570  b31:$F560  4E 70 73  LSR  $7370
03F573  b31:$F563  60        RTS
03F574  b31:$F564  63        .byte $63
03F575  b31:$F565  5D 5E 60  EOR  $605E,X
03F578  b31:$F568  61 70     ADC  ($70,X)
03F57A  b31:$F56A  71 62     ADC  ($62),Y
03F57C  b31:$F56C  63        .byte $63
03F57D  b31:$F56D  72        .byte $72
03F57E  b31:$F56E  73        .byte $73
03F57F  b31:$F56F  4D 4E 5D  EOR  $5D4E
03F582  b31:$F572  5E 62 61  LSR  $6162,X
03F585  b31:$F575  72        .byte $72
03F586  b31:$F576  71 0A     ADC  ($0A),Y
03F588  b31:$F578  27        .byte $27
03F589  b31:$F579  24 25     BIT  $25
03F58B  b31:$F57B  0A        ASL  A
03F58C  b31:$F57C  08        PHP
03F58D  b31:$F57D  36 18     ROL  $18,X
03F58F  b31:$F57F  26 08     ROL  $08
03F591  b31:$F581  0A        ASL  A
03F592  b31:$F582  18        CLC
03F593  b31:$F583  14        .byte $14
03F594  b31:$F584  15 36     ORA  $36,X
03F596  b31:$F586  0A        ASL  A
03F597  b31:$F587  14        .byte $14
03F598  b31:$F588  15 0A     ORA  $0A,X
03F59A  b31:$F58A  37        .byte $37
03F59B  b31:$F58B  07        .byte $07
03F59C  b31:$F58C  27        .byte $27
03F59D  b31:$F58D  17        .byte $17
03F59E  b31:$F58E  0A        ASL  A
03F59F  b31:$F58F  07        .byte $07
03F5A0  b31:$F590  0A        ASL  A
03F5A1  b31:$F591  17        .byte $17
03F5A2  b31:$F592  37        .byte $37
03F5A3  b31:$F593  26 0A     ROL  $0A
03F5A5  b31:$F595  24 25     BIT  $25
03F5A7  b31:$F597  4C 4B 4F  JMP  $4F4B
03F5AA  b31:$F59A  5F        .byte $5F
03F5AB  b31:$F59B  2A        ROL  A
03F5AC  b31:$F59C  4E 72 73  LSR  $7372
03F5AF  b31:$F59F  2A        ROL  A
03F5B0  b31:$F5A0  2B        .byte $2B
03F5B1  b31:$F5A1  72        .byte $72
03F5B2  b31:$F5A2  71 62     ADC  ($62),Y
03F5B4  b31:$F5A4  61 3A     ADC  ($3A,X)
03F5B6  b31:$F5A6  3B        .byte $3B
03F5B7  b31:$F5A7  22        .byte $22
03F5B8  b31:$F5A8  23        .byte $23
03F5B9  b31:$F5A9  32        .byte $32
03F5BA  b31:$F5AA  33        .byte $33
03F5BB  b31:$F5AB  64        .byte $64
03F5BC  b31:$F5AC  23        .byte $23
03F5BD  b31:$F5AD  64        .byte $64
03F5BE  b31:$F5AE  33        .byte $33
03F5BF  b31:$F5AF  22        .byte $22
03F5C0  b31:$F5B0  74        .byte $74
03F5C1  b31:$F5B1  32        .byte $32
03F5C2  b31:$F5B2  74        .byte $74
03F5C3  b31:$F5B3  65 65     ADC  $65
03F5C5  b31:$F5B5  32        .byte $32
03F5C6  b31:$F5B6  33        .byte $33
03F5C7  b31:$F5B7  22        .byte $22
03F5C8  b31:$F5B8  23        .byte $23
03F5C9  b31:$F5B9  75 75     ADC  $75,X
03F5CB  b31:$F5BB  66 66     ROR  $66
03F5CD  b31:$F5BD  65 33     ADC  $33
03F5CF  b31:$F5BF  22        .byte $22
03F5D0  b31:$F5C0  75 66     ADC  $66,X
03F5D2  b31:$F5C2  66 66     ROR  $66
03F5D4  b31:$F5C4  23        .byte $23
03F5D5  b31:$F5C5  66 64     ROR  $64
03F5D7  b31:$F5C7  22        .byte $22
03F5D8  b31:$F5C8  66 74     ROR  $74
03F5DA  b31:$F5CA  66 22     ROR  $22
03F5DC  b31:$F5CC  23        .byte $23
03F5DD  b31:$F5CD  55 33     EOR  $33,X
03F5DF  b31:$F5CF  2C 2D 67  BIT  $672D
03F5E2  b31:$F5D2  3D 0B 35  AND  $350B,X
03F5E5  b31:$F5D5  19 33 22  ORA  $2233,Y
03F5E8  b31:$F5D8  06 04     ASL  $04
03F5EA  b31:$F5DA  76 43     ROR  $43,X
03F5EC  b31:$F5DC  68        PLA
03F5ED  b31:$F5DD  53        .byte $53
03F5EE  b31:$F5DE  78        SEI
03F5EF  b31:$F5DF  09 23     ORA  #$23
03F5F1  b31:$F5E1  77        .byte $77
03F5F2  b31:$F5E2  05 6A     ORA  $6A
03F5F4  b31:$F5E4  0D 7A 1D  ORA  $1D7A
03F5F7  b31:$F5E7  6B        .byte $6B
03F5F8  b31:$F5E8  2D 7B 3D  AND  $3D7B
03F5FB  b31:$F5EB  69 21     ADC  #$21
03F5FD  b31:$F5ED  79 31 0A  ADC  $0A31,Y
03F600  b31:$F5F0  0A        ASL  A
03F601  b31:$F5F1  0A        ASL  A
03F602  b31:$F5F2  0A        ASL  A
03F603  b31:$F5F3  4D 3B 5D  EOR  $5D3B
03F606  b31:$F5F6  3B        .byte $3B
03F607  b31:$F5F7  22        .byte $22
03F608  b31:$F5F8  23        .byte $23
03F609  b31:$F5F9  32        .byte $32
03F60A  b31:$F5FA  33        .byte $33
03F60B  b31:$F5FB  22        .byte $22
03F60C  b31:$F5FC  23        .byte $23
03F60D  b31:$F5FD  32        .byte $32
03F60E  b31:$F5FE  33        .byte $33
03F60F  b31:$F5FF  8C 8D 86  STY  $868D
03F612  b31:$F602  87        .byte $87
03F613  b31:$F603  88        DEY
03F614  b31:$F604  89        .byte $89
03F615  b31:$F605  8C 8D 8A  STY  $8A8D
03F618  b31:$F608  8B        .byte $8B
03F619  b31:$F609  8E 8F 14  STX  $148F
03F61C  b31:$F60C  13        .byte $13
03F61D  b31:$F60D  24 1B     BIT  $1B
03F61F  b31:$F60F  3B        .byte $3B
03F620  b31:$F610  4E 3B 5E  LSR  $5E3B
03F623  b31:$F613  12        .byte $12
03F624  b31:$F614  13        .byte $13
03F625  b31:$F615  17        .byte $17
03F626  b31:$F616  18        CLC
03F627  b31:$F617  D2        .byte $D2
03F628  b31:$F618  15 1A     ORA  $1A,X
03F62A  b31:$F61A  25 17     AND  $17
03F62C  b31:$F61C  18        CLC
03F62D  b31:$F61D  1A        .byte $1A
03F62E  b31:$F61E  1B        .byte $1B
03F62F  b31:$F61F  6C 01 01  JMP  ($0101)
03F632  b31:$F622  01 01     ORA  ($01,X)
03F634  b31:$F624  01 7C     ORA  ($7C,X)
03F636  b31:$F626  01 01     ORA  ($01,X)
03F638  b31:$F628  6D 01 01  ADC  $0101
03F63B  b31:$F62B  01 01     ORA  ($01,X)
03F63D  b31:$F62D  01 7D     ORA  ($7D,X)
03F63F  b31:$F62F  6E 23 7E  ROR  $7E23
03F642  b31:$F632  33        .byte $33
03F643  b31:$F633  23        .byte $23
03F644  b31:$F634  6F        .byte $6F
03F645  b31:$F635  33        .byte $33
03F646  b31:$F636  7F        .byte $7F
03F647  b31:$F637  01 6D     ORA  ($6D,X)
03F649  b31:$F639  01 7D     ORA  ($7D,X)
03F64B  b31:$F63B  6E 23 23  ROR  $2323
03F64E  b31:$F63E  23        .byte $23
03F64F  b31:$F63F  6E 33 23  ROR  $2333
03F652  b31:$F642  33        .byte $33
03F653  b31:$F643  33        .byte $33
03F654  b31:$F644  6F        .byte $6F
03F655  b31:$F645  33        .byte $33
03F656  b31:$F646  33        .byte $33
03F657  b31:$F647  01 01     ORA  ($01,X)
03F659  b31:$F649  7C        .byte $7C
03F65A  b31:$F64A  7D 33 6F  ADC  $6F33,X
03F65D  b31:$F64D  33        .byte $33
03F65E  b31:$F64E  33        .byte $33
03F65F  b31:$F64F  6E 6F 22  ROR  $226F
03F662  b31:$F652  22        .byte $22
03F663  b31:$F653  26 0A     ROL  $0A
03F665  b31:$F655  0A        ASL  A
03F666  b31:$F656  37        .byte $37
03F667  b31:$F657  0A        ASL  A
03F668  b31:$F658  27        .byte $27
03F669  b31:$F659  36 0A     ROL  $0A,X
03F66B  b31:$F65B  22        .byte $22
03F66C  b31:$F65C  23        .byte $23
03F66D  b31:$F65D  32        .byte $32
03F66E  b31:$F65E  33        .byte $33
03F66F  b31:$F65F  22        .byte $22
03F670  b31:$F660  23        .byte $23
03F671  b31:$F661  32        .byte $32
03F672  b31:$F662  33        .byte $33
03F673  b31:$F663  22        .byte $22
03F674  b31:$F664  23        .byte $23
03F675  b31:$F665  32        .byte $32
03F676  b31:$F666  33        .byte $33
03F677  b31:$F667  00        BRK
03F678  b31:$F668  00        BRK
03F679  b31:$F669  00        BRK
03F67A  b31:$F66A  00        BRK
03F67B  b31:$F66B  00        BRK
03F67C  b31:$F66C  00        BRK
03F67D  b31:$F66D  00        BRK
03F67E  b31:$F66E  00        BRK
03F67F  b31:$F66F  00        BRK
03F680  b31:$F670  00        BRK
03F681  b31:$F671  00        BRK
03F682  b31:$F672  00        BRK
03F683  b31:$F673  00        BRK
03F684  b31:$F674  00        BRK
03F685  b31:$F675  00        BRK
03F686  b31:$F676  00        BRK
03F687  b31:$F677  00        BRK
03F688  b31:$F678  00        BRK
03F689  b31:$F679  00        BRK
03F68A  b31:$F67A  00        BRK
03F68B  b31:$F67B  00        BRK
03F68C  b31:$F67C  00        BRK
03F68D  b31:$F67D  00        BRK
03F68E  b31:$F67E  00        BRK
03F68F  b31:$F67F  FF        .byte $FF
03F690  b31:$F680  FF        .byte $FF
03F691  b31:$F681  FF        .byte $FF
03F692  b31:$F682  FF        .byte $FF
03F693  b31:$F683  FF        .byte $FF
03F694  b31:$F684  FF        .byte $FF
03F695  b31:$F685  FF        .byte $FF
03F696  b31:$F686  FF        .byte $FF
03F697  b31:$F687  FF        .byte $FF
03F698  b31:$F688  FF        .byte $FF
03F699  b31:$F689  FF        .byte $FF
03F69A  b31:$F68A  FF        .byte $FF
03F69B  b31:$F68B  FF        .byte $FF
03F69C  b31:$F68C  FF        .byte $FF
03F69D  b31:$F68D  FF        .byte $FF
03F69E  b31:$F68E  FF        .byte $FF
03F69F  b31:$F68F  FF        .byte $FF
03F6A0  b31:$F690  FF        .byte $FF
03F6A1  b31:$F691  FF        .byte $FF
03F6A2  b31:$F692  FF        .byte $FF
03F6A3  b31:$F693  FF        .byte $FF
03F6A4  b31:$F694  FF        .byte $FF
03F6A5  b31:$F695  FF        .byte $FF
03F6A6  b31:$F696  FF        .byte $FF
03F6A7  b31:$F697  FF        .byte $FF
03F6A8  b31:$F698  FF        .byte $FF
03F6A9  b31:$F699  FF        .byte $FF
03F6AA  b31:$F69A  FF        .byte $FF
03F6AB  b31:$F69B  FF        .byte $FF
03F6AC  b31:$F69C  FF        .byte $FF
03F6AD  b31:$F69D  FF        .byte $FF
03F6AE  b31:$F69E  FF        .byte $FF
03F6AF  b31:$F69F  FF        .byte $FF
03F6B0  b31:$F6A0  FF        .byte $FF
03F6B1  b31:$F6A1  FF        .byte $FF
03F6B2  b31:$F6A2  FF        .byte $FF
03F6B3  b31:$F6A3  FF        .byte $FF
03F6B4  b31:$F6A4  FF        .byte $FF
03F6B5  b31:$F6A5  FF        .byte $FF
03F6B6  b31:$F6A6  FF        .byte $FF
03F6B7  b31:$F6A7  FF        .byte $FF
03F6B8  b31:$F6A8  FF        .byte $FF
03F6B9  b31:$F6A9  FF        .byte $FF
03F6BA  b31:$F6AA  FF        .byte $FF
03F6BB  b31:$F6AB  FF        .byte $FF
03F6BC  b31:$F6AC  FF        .byte $FF
03F6BD  b31:$F6AD  FF        .byte $FF
03F6BE  b31:$F6AE  FF        .byte $FF
03F6BF  b31:$F6AF  FF        .byte $FF
03F6C0  b31:$F6B0  FF        .byte $FF
03F6C1  b31:$F6B1  FF        .byte $FF
03F6C2  b31:$F6B2  FF        .byte $FF
03F6C3  b31:$F6B3  FF        .byte $FF
03F6C4  b31:$F6B4  FF        .byte $FF
03F6C5  b31:$F6B5  FF        .byte $FF
03F6C6  b31:$F6B6  FF        .byte $FF
03F6C7  b31:$F6B7  FF        .byte $FF
03F6C8  b31:$F6B8  FF        .byte $FF
03F6C9  b31:$F6B9  FF        .byte $FF
03F6CA  b31:$F6BA  FF        .byte $FF
03F6CB  b31:$F6BB  FF        .byte $FF
03F6CC  b31:$F6BC  FF        .byte $FF
03F6CD  b31:$F6BD  FF        .byte $FF
03F6CE  b31:$F6BE  FF        .byte $FF
03F6CF  b31:$F6BF  FF        .byte $FF
03F6D0  b31:$F6C0  FF        .byte $FF
03F6D1  b31:$F6C1  FF        .byte $FF
03F6D2  b31:$F6C2  FF        .byte $FF
03F6D3  b31:$F6C3  FF        .byte $FF
03F6D4  b31:$F6C4  FF        .byte $FF
03F6D5  b31:$F6C5  FF        .byte $FF
03F6D6  b31:$F6C6  FF        .byte $FF
03F6D7  b31:$F6C7  FF        .byte $FF
03F6D8  b31:$F6C8  FF        .byte $FF
03F6D9  b31:$F6C9  FF        .byte $FF
03F6DA  b31:$F6CA  FF        .byte $FF
03F6DB  b31:$F6CB  FF        .byte $FF
03F6DC  b31:$F6CC  FF        .byte $FF
03F6DD  b31:$F6CD  FF        .byte $FF
03F6DE  b31:$F6CE  FF        .byte $FF
03F6DF  b31:$F6CF  FF        .byte $FF
03F6E0  b31:$F6D0  FF        .byte $FF
03F6E1  b31:$F6D1  FF        .byte $FF
03F6E2  b31:$F6D2  FF        .byte $FF
03F6E3  b31:$F6D3  FF        .byte $FF
03F6E4  b31:$F6D4  FF        .byte $FF
03F6E5  b31:$F6D5  FF        .byte $FF
03F6E6  b31:$F6D6  FF        .byte $FF
03F6E7  b31:$F6D7  FF        .byte $FF
03F6E8  b31:$F6D8  FF        .byte $FF
03F6E9  b31:$F6D9  FF        .byte $FF
03F6EA  b31:$F6DA  FF        .byte $FF
03F6EB  b31:$F6DB  FF        .byte $FF
03F6EC  b31:$F6DC  FF        .byte $FF
03F6ED  b31:$F6DD  FF        .byte $FF
03F6EE  b31:$F6DE  FF        .byte $FF
03F6EF  b31:$F6DF  FF        .byte $FF
03F6F0  b31:$F6E0  FF        .byte $FF
03F6F1  b31:$F6E1  FF        .byte $FF
03F6F2  b31:$F6E2  FF        .byte $FF
03F6F3  b31:$F6E3  FF        .byte $FF
03F6F4  b31:$F6E4  FF        .byte $FF
03F6F5  b31:$F6E5  FF        .byte $FF
03F6F6  b31:$F6E6  FF        .byte $FF
03F6F7  b31:$F6E7  FF        .byte $FF
03F6F8  b31:$F6E8  FF        .byte $FF
03F6F9  b31:$F6E9  FF        .byte $FF
03F6FA  b31:$F6EA  FF        .byte $FF
03F6FB  b31:$F6EB  FF        .byte $FF
03F6FC  b31:$F6EC  FF        .byte $FF
03F6FD  b31:$F6ED  FF        .byte $FF
03F6FE  b31:$F6EE  FF        .byte $FF
03F6FF  b31:$F6EF  FF        .byte $FF
03F700  b31:$F6F0  FF        .byte $FF
03F701  b31:$F6F1  FF        .byte $FF
03F702  b31:$F6F2  FF        .byte $FF
03F703  b31:$F6F3  FF        .byte $FF
03F704  b31:$F6F4  FF        .byte $FF
03F705  b31:$F6F5  FF        .byte $FF
03F706  b31:$F6F6  FF        .byte $FF
03F707  b31:$F6F7  FF        .byte $FF
03F708  b31:$F6F8  FF        .byte $FF
03F709  b31:$F6F9  FF        .byte $FF
03F70A  b31:$F6FA  FF        .byte $FF
03F70B  b31:$F6FB  FF        .byte $FF
03F70C  b31:$F6FC  FF        .byte $FF
03F70D  b31:$F6FD  FF        .byte $FF
03F70E  b31:$F6FE  FF        .byte $FF
03F70F  b31:$F6FF  FF        .byte $FF
03F710  b31:$F700  FF        .byte $FF
03F711  b31:$F701  FF        .byte $FF
03F712  b31:$F702  FF        .byte $FF
03F713  b31:$F703  FF        .byte $FF
03F714  b31:$F704  FF        .byte $FF
03F715  b31:$F705  FF        .byte $FF
03F716  b31:$F706  FF        .byte $FF
03F717  b31:$F707  FF        .byte $FF
03F718  b31:$F708  FF        .byte $FF
03F719  b31:$F709  FF        .byte $FF
03F71A  b31:$F70A  FF        .byte $FF
03F71B  b31:$F70B  FF        .byte $FF
03F71C  b31:$F70C  FF        .byte $FF
03F71D  b31:$F70D  FF        .byte $FF
03F71E  b31:$F70E  FF        .byte $FF
03F71F  b31:$F70F  FF        .byte $FF
03F720  b31:$F710  FF        .byte $FF
03F721  b31:$F711  FF        .byte $FF
03F722  b31:$F712  FF        .byte $FF
03F723  b31:$F713  FF        .byte $FF
03F724  b31:$F714  FF        .byte $FF
03F725  b31:$F715  FF        .byte $FF
03F726  b31:$F716  FF        .byte $FF
03F727  b31:$F717  FF        .byte $FF
03F728  b31:$F718  FF        .byte $FF
03F729  b31:$F719  FF        .byte $FF
03F72A  b31:$F71A  FF        .byte $FF
03F72B  b31:$F71B  FF        .byte $FF
03F72C  b31:$F71C  FF        .byte $FF
03F72D  b31:$F71D  FF        .byte $FF
03F72E  b31:$F71E  FF        .byte $FF
03F72F  b31:$F71F  FF        .byte $FF
03F730  b31:$F720  FF        .byte $FF
03F731  b31:$F721  FF        .byte $FF
03F732  b31:$F722  FF        .byte $FF
03F733  b31:$F723  FF        .byte $FF
03F734  b31:$F724  FF        .byte $FF
03F735  b31:$F725  FF        .byte $FF
03F736  b31:$F726  FF        .byte $FF
03F737  b31:$F727  FF        .byte $FF
03F738  b31:$F728  FF        .byte $FF
03F739  b31:$F729  FF        .byte $FF
03F73A  b31:$F72A  FF        .byte $FF
03F73B  b31:$F72B  FF        .byte $FF
03F73C  b31:$F72C  FF        .byte $FF
03F73D  b31:$F72D  FF        .byte $FF
03F73E  b31:$F72E  FF        .byte $FF
03F73F  b31:$F72F  FF        .byte $FF
03F740  b31:$F730  FF        .byte $FF
03F741  b31:$F731  FF        .byte $FF
03F742  b31:$F732  FF        .byte $FF
03F743  b31:$F733  FF        .byte $FF
03F744  b31:$F734  FF        .byte $FF
03F745  b31:$F735  FF        .byte $FF
03F746  b31:$F736  FF        .byte $FF
03F747  b31:$F737  FF        .byte $FF
03F748  b31:$F738  FF        .byte $FF
03F749  b31:$F739  FF        .byte $FF
03F74A  b31:$F73A  FF        .byte $FF
03F74B  b31:$F73B  FF        .byte $FF
03F74C  b31:$F73C  FF        .byte $FF
03F74D  b31:$F73D  FF        .byte $FF
03F74E  b31:$F73E  FF        .byte $FF
03F74F  b31:$F73F  FF        .byte $FF
03F750  b31:$F740  FF        .byte $FF
03F751  b31:$F741  FF        .byte $FF
03F752  b31:$F742  FF        .byte $FF
03F753  b31:$F743  FF        .byte $FF
03F754  b31:$F744  FF        .byte $FF
03F755  b31:$F745  FF        .byte $FF
03F756  b31:$F746  FF        .byte $FF
03F757  b31:$F747  FF        .byte $FF
03F758  b31:$F748  FF        .byte $FF
03F759  b31:$F749  FF        .byte $FF
03F75A  b31:$F74A  FF        .byte $FF
03F75B  b31:$F74B  FF        .byte $FF
03F75C  b31:$F74C  FF        .byte $FF
03F75D  b31:$F74D  FF        .byte $FF
03F75E  b31:$F74E  FF        .byte $FF
03F75F  b31:$F74F  FF        .byte $FF
03F760  b31:$F750  FF        .byte $FF
03F761  b31:$F751  FF        .byte $FF
03F762  b31:$F752  FF        .byte $FF
03F763  b31:$F753  FF        .byte $FF
03F764  b31:$F754  FF        .byte $FF
03F765  b31:$F755  FF        .byte $FF
03F766  b31:$F756  FF        .byte $FF
03F767  b31:$F757  FF        .byte $FF
03F768  b31:$F758  FF        .byte $FF
03F769  b31:$F759  FF        .byte $FF
03F76A  b31:$F75A  FF        .byte $FF
03F76B  b31:$F75B  FF        .byte $FF
03F76C  b31:$F75C  FF        .byte $FF
03F76D  b31:$F75D  FF        .byte $FF
03F76E  b31:$F75E  FF        .byte $FF
03F76F  b31:$F75F  FF        .byte $FF
03F770  b31:$F760  FF        .byte $FF
03F771  b31:$F761  FF        .byte $FF
03F772  b31:$F762  FF        .byte $FF
03F773  b31:$F763  FF        .byte $FF
03F774  b31:$F764  FF        .byte $FF
03F775  b31:$F765  FF        .byte $FF
03F776  b31:$F766  FF        .byte $FF
03F777  b31:$F767  FF        .byte $FF
03F778  b31:$F768  FF        .byte $FF
03F779  b31:$F769  FF        .byte $FF
03F77A  b31:$F76A  FF        .byte $FF
03F77B  b31:$F76B  FF        .byte $FF
03F77C  b31:$F76C  FF        .byte $FF
03F77D  b31:$F76D  FF        .byte $FF
03F77E  b31:$F76E  FF        .byte $FF
03F77F  b31:$F76F  FF        .byte $FF
03F780  b31:$F770  FF        .byte $FF
03F781  b31:$F771  FF        .byte $FF
03F782  b31:$F772  FF        .byte $FF
03F783  b31:$F773  FF        .byte $FF
03F784  b31:$F774  FF        .byte $FF
03F785  b31:$F775  FF        .byte $FF
03F786  b31:$F776  FF        .byte $FF
03F787  b31:$F777  FF        .byte $FF
03F788  b31:$F778  FF        .byte $FF
03F789  b31:$F779  FF        .byte $FF
03F78A  b31:$F77A  FF        .byte $FF
03F78B  b31:$F77B  FF        .byte $FF
03F78C  b31:$F77C  FF        .byte $FF
03F78D  b31:$F77D  FF        .byte $FF
03F78E  b31:$F77E  FF        .byte $FF
03F78F  b31:$F77F  FF        .byte $FF
03F790  b31:$F780  FF        .byte $FF
03F791  b31:$F781  FF        .byte $FF
03F792  b31:$F782  FF        .byte $FF
03F793  b31:$F783  FF        .byte $FF
03F794  b31:$F784  FF        .byte $FF
03F795  b31:$F785  FF        .byte $FF
03F796  b31:$F786  FF        .byte $FF
03F797  b31:$F787  FF        .byte $FF
03F798  b31:$F788  FF        .byte $FF
03F799  b31:$F789  FF        .byte $FF
03F79A  b31:$F78A  FF        .byte $FF
03F79B  b31:$F78B  FF        .byte $FF
03F79C  b31:$F78C  FF        .byte $FF
03F79D  b31:$F78D  FF        .byte $FF
03F79E  b31:$F78E  FF        .byte $FF
03F79F  b31:$F78F  FF        .byte $FF
03F7A0  b31:$F790  FF        .byte $FF
03F7A1  b31:$F791  FF        .byte $FF
03F7A2  b31:$F792  FF        .byte $FF
03F7A3  b31:$F793  FF        .byte $FF
03F7A4  b31:$F794  FF        .byte $FF
03F7A5  b31:$F795  FF        .byte $FF
03F7A6  b31:$F796  FF        .byte $FF
03F7A7  b31:$F797  FF        .byte $FF
03F7A8  b31:$F798  FF        .byte $FF
03F7A9  b31:$F799  FF        .byte $FF
03F7AA  b31:$F79A  FF        .byte $FF
03F7AB  b31:$F79B  FF        .byte $FF
03F7AC  b31:$F79C  FF        .byte $FF
03F7AD  b31:$F79D  FF        .byte $FF
03F7AE  b31:$F79E  FF        .byte $FF
03F7AF  b31:$F79F  FF        .byte $FF
03F7B0  b31:$F7A0  FF        .byte $FF
03F7B1  b31:$F7A1  FF        .byte $FF
03F7B2  b31:$F7A2  FF        .byte $FF
03F7B3  b31:$F7A3  FF        .byte $FF
03F7B4  b31:$F7A4  FF        .byte $FF
03F7B5  b31:$F7A5  FF        .byte $FF
03F7B6  b31:$F7A6  FF        .byte $FF
03F7B7  b31:$F7A7  FF        .byte $FF
03F7B8  b31:$F7A8  FF        .byte $FF
03F7B9  b31:$F7A9  FF        .byte $FF
03F7BA  b31:$F7AA  FF        .byte $FF
03F7BB  b31:$F7AB  FF        .byte $FF
03F7BC  b31:$F7AC  FF        .byte $FF
03F7BD  b31:$F7AD  FF        .byte $FF
03F7BE  b31:$F7AE  FF        .byte $FF
03F7BF  b31:$F7AF  FF        .byte $FF
03F7C0  b31:$F7B0  FF        .byte $FF
03F7C1  b31:$F7B1  FF        .byte $FF
03F7C2  b31:$F7B2  FF        .byte $FF
03F7C3  b31:$F7B3  FF        .byte $FF
03F7C4  b31:$F7B4  FF        .byte $FF
03F7C5  b31:$F7B5  FF        .byte $FF
03F7C6  b31:$F7B6  FF        .byte $FF
03F7C7  b31:$F7B7  FF        .byte $FF
03F7C8  b31:$F7B8  FF        .byte $FF
03F7C9  b31:$F7B9  FF        .byte $FF
03F7CA  b31:$F7BA  FF        .byte $FF
03F7CB  b31:$F7BB  FF        .byte $FF
03F7CC  b31:$F7BC  FF        .byte $FF
03F7CD  b31:$F7BD  FF        .byte $FF
03F7CE  b31:$F7BE  FF        .byte $FF
03F7CF  b31:$F7BF  FF        .byte $FF
03F7D0  b31:$F7C0  FF        .byte $FF
03F7D1  b31:$F7C1  FF        .byte $FF
03F7D2  b31:$F7C2  FF        .byte $FF
03F7D3  b31:$F7C3  FF        .byte $FF
03F7D4  b31:$F7C4  FF        .byte $FF
03F7D5  b31:$F7C5  FF        .byte $FF
03F7D6  b31:$F7C6  FF        .byte $FF
03F7D7  b31:$F7C7  FF        .byte $FF
03F7D8  b31:$F7C8  FF        .byte $FF
03F7D9  b31:$F7C9  FF        .byte $FF
03F7DA  b31:$F7CA  FF        .byte $FF
03F7DB  b31:$F7CB  FF        .byte $FF
03F7DC  b31:$F7CC  FF        .byte $FF
03F7DD  b31:$F7CD  FF        .byte $FF
03F7DE  b31:$F7CE  FF        .byte $FF
03F7DF  b31:$F7CF  FF        .byte $FF
03F7E0  b31:$F7D0  FF        .byte $FF
03F7E1  b31:$F7D1  FF        .byte $FF
03F7E2  b31:$F7D2  FF        .byte $FF
03F7E3  b31:$F7D3  FF        .byte $FF
03F7E4  b31:$F7D4  FF        .byte $FF
03F7E5  b31:$F7D5  FF        .byte $FF
03F7E6  b31:$F7D6  FF        .byte $FF
03F7E7  b31:$F7D7  FF        .byte $FF
03F7E8  b31:$F7D8  FF        .byte $FF
03F7E9  b31:$F7D9  FF        .byte $FF
03F7EA  b31:$F7DA  FF        .byte $FF
03F7EB  b31:$F7DB  FF        .byte $FF
03F7EC  b31:$F7DC  FF        .byte $FF
03F7ED  b31:$F7DD  FF        .byte $FF
03F7EE  b31:$F7DE  FF        .byte $FF
03F7EF  b31:$F7DF  FF        .byte $FF
03F7F0  b31:$F7E0  FF        .byte $FF
03F7F1  b31:$F7E1  FF        .byte $FF
03F7F2  b31:$F7E2  FF        .byte $FF
03F7F3  b31:$F7E3  FF        .byte $FF
03F7F4  b31:$F7E4  FF        .byte $FF
03F7F5  b31:$F7E5  FF        .byte $FF
03F7F6  b31:$F7E6  FF        .byte $FF
03F7F7  b31:$F7E7  FF        .byte $FF
03F7F8  b31:$F7E8  FF        .byte $FF
03F7F9  b31:$F7E9  FF        .byte $FF
03F7FA  b31:$F7EA  FF        .byte $FF
03F7FB  b31:$F7EB  FF        .byte $FF
03F7FC  b31:$F7EC  FF        .byte $FF
03F7FD  b31:$F7ED  FF        .byte $FF
03F7FE  b31:$F7EE  FF        .byte $FF
03F7FF  b31:$F7EF  FF        .byte $FF
03F800  b31:$F7F0  FF        .byte $FF
03F801  b31:$F7F1  FF        .byte $FF
03F802  b31:$F7F2  FF        .byte $FF
03F803  b31:$F7F3  FF        .byte $FF
03F804  b31:$F7F4  FF        .byte $FF
03F805  b31:$F7F5  FF        .byte $FF
03F806  b31:$F7F6  FF        .byte $FF
03F807  b31:$F7F7  FF        .byte $FF
03F808  b31:$F7F8  FF        .byte $FF
03F809  b31:$F7F9  FF        .byte $FF
03F80A  b31:$F7FA  FF        .byte $FF
03F80B  b31:$F7FB  FF        .byte $FF
03F80C  b31:$F7FC  FF        .byte $FF
03F80D  b31:$F7FD  FF        .byte $FF
03F80E  b31:$F7FE  FF        .byte $FF
03F80F  b31:$F7FF  FF        .byte $FF
