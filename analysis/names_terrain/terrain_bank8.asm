011630  b08:$B620  21 1E     AND  ($1E,X)
011632  b08:$B622  B4 8C     LDY  $8C,X
011634  b08:$B624  CE 7B FE  DEC  $FE7B
011637  b08:$B627  22        .byte $22
011638  b08:$B628  DC        .byte $DC
011639  b08:$B629  18        CLC
01163A  b08:$B62A  C4 6D     CPY  $6D
01163C  b08:$B62C  FB        .byte $FB
01163D  b08:$B62D  CD 27 A0  CMP  $A027
011640  b08:$B630  09 6E     ORA  #$6E
011642  b08:$B632  38        SEC
011643  b08:$B633  8A        TXA
011644  b08:$B634  04        .byte $04
011645  b08:$B635  7C        .byte $7C
011646  b08:$B636  56 97     LSR  $97,X
011648  b08:$B638  5A        .byte $5A
011649  b08:$B639  A8        TAY
01164A  b08:$B63A  4D 78 B5  EOR  $B578
01164D  b08:$B63D  6C AA 03  JMP  ($03AA)
011650  b08:$B640  1A        .byte $1A
011651  b08:$B641  4A        LSR  A
011652  b08:$B642  0D 26 82  ORA  $8226
011655  b08:$B645  AD 02 A1  LDA  $A102
011658  b08:$B648  B9 A3 6B  LDA  $6BA3,Y
01165B  b08:$B64B  D8        CLD
01165C  b08:$B64C  0C        .byte $0C
01165D  b08:$B64D  4C AE 19  JMP  $19AE
011660  b08:$B650  45 5B     EOR  $5B
011662  b08:$B652  9C        .byte $9C
011663  b08:$B653  16 07     ASL  $07,X
011665  b08:$B655  89        .byte $89
011666  b08:$B656  51 90     EOR  ($90),Y
011668  b08:$B658  29 F5     AND  #$F5
01166A  b08:$B65A  62        .byte $62
01166B  b08:$B65B  F7        .byte $F7
01166C  b08:$B65C  CB        .byte $CB
01166D  b08:$B65D  F1 53     SBC  ($53),Y
01166F  b08:$B65F  FF        .byte $FF
011670  b08:$B660  14        .byte $14
011671  b08:$B661  65 D0     ADC  $D0
011673  b08:$B663  87        .byte $87
011674  b08:$B664  35 10     AND  $10,X
011676  b08:$B666  73        .byte $73
011677  b08:$B667  7A        .byte $7A
011678  b08:$B668  9F        .byte $9F
011679  b08:$B669  EB        .byte $EB
01167A  b08:$B66A  D9 3C EF  CMP  $EF3C,Y
01167D  b08:$B66D  9E        .byte $9E
01167E  b08:$B66E  D7        .byte $D7
01167F  b08:$B66F  3D 6F D6  AND  $D66F,X
011682  b08:$B672  84 AB     STY  $AB
011684  b08:$B674  11 CA     ORA  ($CA),Y
011686  b08:$B676  D2        .byte $D2
011687  b08:$B677  88        DEY
011688  b08:$B678  17        .byte $17
011689  b08:$B679  E1 A6     SBC  ($A6,X)
01168B  b08:$B67B  52        .byte $52
01168C  b08:$B67C  8E 5E 36  STX  $365E
01168F  b08:$B67F  24 44     BIT  $44
011691  b08:$B681  28        PLP
011692  b08:$B682  A4 55     LDY  $55
011694  b08:$B684  A7        .byte $A7
011695  b08:$B685  C2        .byte $C2
011696  b08:$B686  FD 76 2E  SBC  $2E76,X
011699  b08:$B689  B7        .byte $B7
01169A  b08:$B68A  D5 F6     CMP  $F6,X
01169C  b08:$B68C  64        .byte $64
01169D  b08:$B68D  15 31     ORA  $31,X
01169F  b08:$B68F  99 93 C0  STA  $C093,Y
0116A2  b08:$B692  8F        .byte $8F
0116A3  b08:$B693  B3        .byte $B3
0116A4  b08:$B694  FA        .byte $FA
0116A5  b08:$B695  E9 E3     SBC  #$E3
0116A7  b08:$B697  67        .byte $67
0116A8  b08:$B698  4B        .byte $4B
0116A9  b08:$B699  85 32     STA  $32
0116AB  b08:$B69B  C6 69     DEC  $69
0116AD  b08:$B69D  48        PHA
0116AE  b08:$B69E  DF        .byte $DF
0116AF  b08:$B69F  A2 EC     LDX  #$EC
0116B1  b08:$B6A1  98        TYA
0116B2  b08:$B6A2  6A        ROR  A
0116B3  b08:$B6A3  E7        .byte $E7
0116B4  b08:$B6A4  D4        .byte $D4
0116B5  b08:$B6A5  1C        .byte $1C
0116B6  b08:$B6A6  F3        .byte $F3
0116B7  b08:$B6A7  58        CLI
0116B8  b08:$B6A8  50 ED     BVC  $B697
0116BA  b08:$B6AA  2B        .byte $2B
0116BB  b08:$B6AB  1D 86 F0  ORA  $F086,X
0116BE  b08:$B6AE  71 BD     ADC  ($BD),Y
0116C0  b08:$B6B0  34        .byte $34
0116C1  b08:$B6B1  1B        .byte $1B
0116C2  b08:$B6B2  AF        .byte $AF
0116C3  b08:$B6B3  30 2D     BMI  $B6E2
0116C5  b08:$B6B5  68        PLA
0116C6  b08:$B6B6  CC 0F 57  CPY  $570F
0116C9  b08:$B6B9  EA        NOP
0116CA  b08:$B6BA  92        .byte $92
0116CB  b08:$B6BB  8B        .byte $8B
0116CC  b08:$B6BC  3F        .byte $3F
0116CD  b08:$B6BD  3B        .byte $3B
0116CE  b08:$B6BE  AC B8 C1  LDY  $C1B8
0116D1  b08:$B6C1  2F        .byte $2F
0116D2  b08:$B6C2  F2        .byte $F2
0116D3  b08:$B6C3  46 75     LSR  $75
0116D5  b08:$B6C5  96 7D     STX  $7D,Y
0116D7  b08:$B6C7  2A        ROL  A
0116D8  b08:$B6C8  79 40 DA  ADC  $DA40,Y
0116DB  b08:$B6CB  9D 25 12  STA  $1225,X
0116DE  b08:$B6CE  42        .byte $42
0116DF  b08:$B6CF  54        .byte $54
0116E0  b08:$B6D0  D3        .byte $D3
0116E1  b08:$B6D1  1F        .byte $1F
0116E2  b08:$B6D2  80        .byte $80
0116E3  b08:$B6D3  5C        .byte $5C
0116E4  b08:$B6D4  59 43 F9  EOR  $F943,Y
0116E7  b08:$B6D7  B0 DD     BCS  $B6B6
0116E9  b08:$B6D9  63        .byte $63
0116EA  b08:$B6DA  A5 77     LDA  $77
0116EC  b08:$B6DC  CF        .byte $CF
0116ED  b08:$B6DD  13        .byte $13
0116EE  b08:$B6DE  2C 66 BC  BIT  $BC66
0116F1  b08:$B6E1  70 B1     BVS  $B694
0116F3  b08:$B6E3  C5 06     CMP  $06
0116F5  b08:$B6E5  20 EF B6  JSR  $B6EF
0116F8  b08:$B6E8  C9 06     CMP  #$06
0116FA  b08:$B6EA  90 02     BCC  $B6EE
0116FC  b08:$B6EC  A9 02     LDA  #$02
0116FE  b08:$B6EE  60        RTS
0116FF  b08:$B6EF  A0 00     LDY  #$00
011701  b08:$B6F1  AD 20 00  LDA  $0020
011704  b08:$B6F4  C9 10     CMP  #$10
011706  b08:$B6F6  90 02     BCC  $B6FA
011708  b08:$B6F8  A0 01     LDY  #$01
01170A  b08:$B6FA  AD 21 00  LDA  $0021
01170D  b08:$B6FD  C9 10     CMP  #$10
01170F  b08:$B6FF  90 04     BCC  $B705
011711  b08:$B701  98        TYA
011712  b08:$B702  09 02     ORA  #$02
011714  b08:$B704  A8        TAY
011715  b08:$B705  B1 A8     LDA  ($A8),Y
011717  b08:$B707  48        PHA
011718  b08:$B708  0A        ASL  A
011719  b08:$B709  A8        TAY
01171A  b08:$B70A  B9 CB B7  LDA  $B7CB,Y
01171D  b08:$B70D  8D 22 00  STA  $0022
011720  b08:$B710  B9 CC B7  LDA  $B7CC,Y
011723  b08:$B713  8D 23 00  STA  $0023
011726  b08:$B716  68        PLA
011727  b08:$B717  A8        TAY
011728  b08:$B718  B9 BB B8  LDA  $B8BB,Y
01172B  b08:$B71B  A8        TAY
01172C  b08:$B71C  20 66 F2  JSR  $F266
01172F  b08:$B71F  A9 4B     LDA  #$4B
011731  b08:$B721  8D 24 00  STA  $0024
011734  b08:$B724  A9 B7     LDA  #$B7
011736  b08:$B726  8D 25 00  STA  $0025
011739  b08:$B729  AD 20 00  LDA  $0020
01173C  b08:$B72C  29 0F     AND  #$0F
01173E  b08:$B72E  8D 26 00  STA  $0026
011741  b08:$B731  A2 00     LDX  #$00
011743  b08:$B733  AD 21 00  LDA  $0021
011746  b08:$B736  0A        ASL  A
011747  b08:$B737  0A        ASL  A
011748  b08:$B738  0A        ASL  A
011749  b08:$B739  0A        ASL  A
01174A  b08:$B73A  0D 26 00  ORA  $0026
01174D  b08:$B73D  A8        TAY
01174E  b08:$B73E  B1 22     LDA  ($22),Y
011750  b08:$B740  A8        TAY
011751  b08:$B741  C9 80     CMP  #$80
011753  b08:$B743  90 03     BCC  $B748
011755  b08:$B745  A9 00     LDA  #$00
011757  b08:$B747  60        RTS
011758  b08:$B748  B1 24     LDA  ($24),Y
01175A  b08:$B74A  60        RTS
01175B  b08:$B74B  00        BRK
01175C  b08:$B74C  01 03     ORA  ($03,X)
01175E  b08:$B74E  03        .byte $03
01175F  b08:$B74F  03        .byte $03
011760  b08:$B750  03        .byte $03
011761  b08:$B751  03        .byte $03
011762  b08:$B752  03        .byte $03
011763  b08:$B753  03        .byte $03
011764  b08:$B754  03        .byte $03
011765  b08:$B755  03        .byte $03
011766  b08:$B756  03        .byte $03
011767  b08:$B757  03        .byte $03
011768  b08:$B758  03        .byte $03
011769  b08:$B759  03        .byte $03
01176A  b08:$B75A  03        .byte $03
01176B  b08:$B75B  03        .byte $03
01176C  b08:$B75C  03        .byte $03
01176D  b08:$B75D  03        .byte $03
01176E  b08:$B75E  03        .byte $03
01176F  b08:$B75F  03        .byte $03
011770  b08:$B760  03        .byte $03
011771  b08:$B761  03        .byte $03
011772  b08:$B762  03        .byte $03
011773  b08:$B763  03        .byte $03
011774  b08:$B764  03        .byte $03
011775  b08:$B765  03        .byte $03
011776  b08:$B766  03        .byte $03
011777  b08:$B767  02        .byte $02
011778  b08:$B768  02        .byte $02
011779  b08:$B769  02        .byte $02
01177A  b08:$B76A  02        .byte $02
01177B  b08:$B76B  04        .byte $04
01177C  b08:$B76C  04        .byte $04
01177D  b08:$B76D  02        .byte $02
01177E  b08:$B76E  04        .byte $04
01177F  b08:$B76F  04        .byte $04
011780  b08:$B770  02        .byte $02
011781  b08:$B771  04        .byte $04
011782  b08:$B772  02        .byte $02
011783  b08:$B773  04        .byte $04
011784  b08:$B774  04        .byte $04
011785  b08:$B775  04        .byte $04
011786  b08:$B776  02        .byte $02
011787  b08:$B777  00        BRK
011788  b08:$B778  00        BRK
011789  b08:$B779  02        .byte $02
01178A  b08:$B77A  02        .byte $02
01178B  b08:$B77B  02        .byte $02
01178C  b08:$B77C  02        .byte $02
01178D  b08:$B77D  02        .byte $02
01178E  b08:$B77E  02        .byte $02
01178F  b08:$B77F  02        .byte $02
011790  b08:$B780  02        .byte $02
011791  b08:$B781  00        BRK
011792  b08:$B782  00        BRK
011793  b08:$B783  00        BRK
011794  b08:$B784  02        .byte $02
011795  b08:$B785  00        BRK
011796  b08:$B786  00        BRK
011797  b08:$B787  00        BRK
011798  b08:$B788  00        BRK
011799  b08:$B789  00        BRK
01179A  b08:$B78A  00        BRK
01179B  b08:$B78B  03        .byte $03
01179C  b08:$B78C  03        .byte $03
01179D  b08:$B78D  03        .byte $03
01179E  b08:$B78E  03        .byte $03
01179F  b08:$B78F  03        .byte $03
0117A0  b08:$B790  03        .byte $03
0117A1  b08:$B791  03        .byte $03
0117A2  b08:$B792  03        .byte $03
0117A3  b08:$B793  02        .byte $02
0117A4  b08:$B794  00        BRK
0117A5  b08:$B795  00        BRK
0117A6  b08:$B796  00        BRK
0117A7  b08:$B797  02        .byte $02
0117A8  b08:$B798  02        .byte $02
0117A9  b08:$B799  02        .byte $02
0117AA  b08:$B79A  02        .byte $02
0117AB  b08:$B79B  02        .byte $02
0117AC  b08:$B79C  02        .byte $02
0117AD  b08:$B79D  02        .byte $02
0117AE  b08:$B79E  02        .byte $02
0117AF  b08:$B79F  02        .byte $02
0117B0  b08:$B7A0  02        .byte $02
0117B1  b08:$B7A1  04        .byte $04
0117B2  b08:$B7A2  02        .byte $02
0117B3  b08:$B7A3  02        .byte $02
0117B4  b08:$B7A4  04        .byte $04
0117B5  b08:$B7A5  02        .byte $02
0117B6  b08:$B7A6  04        .byte $04
0117B7  b08:$B7A7  04        .byte $04
0117B8  b08:$B7A8  04        .byte $04
0117B9  b08:$B7A9  03        .byte $03
0117BA  b08:$B7AA  00        BRK
0117BB  b08:$B7AB  00        BRK
0117BC  b08:$B7AC  05 05     ORA  $05
0117BE  b08:$B7AE  05 05     ORA  $05
0117C0  b08:$B7B0  03        .byte $03
0117C1  b08:$B7B1  00        BRK
0117C2  b08:$B7B2  03        .byte $03
0117C3  b08:$B7B3  03        .byte $03
0117C4  b08:$B7B4  03        .byte $03
0117C5  b08:$B7B5  01 01     ORA  ($01,X)
0117C7  b08:$B7B7  01 01     ORA  ($01,X)
0117C9  b08:$B7B9  02        .byte $02
0117CA  b08:$B7BA  02        .byte $02
0117CB  b08:$B7BB  01 02     ORA  ($02,X)
0117CD  b08:$B7BD  02        .byte $02
0117CE  b08:$B7BE  02        .byte $02
0117CF  b08:$B7BF  01 02     ORA  ($02,X)
0117D1  b08:$B7C1  02        .byte $02
0117D2  b08:$B7C2  03        .byte $03
0117D3  b08:$B7C3  03        .byte $03
0117D4  b08:$B7C4  06 07     ASL  $07
0117D6  b08:$B7C6  08        PHP
0117D7  b08:$B7C7  00        BRK
0117D8  b08:$B7C8  00        BRK
0117D9  b08:$B7C9  00        BRK
0117DA  b08:$B7CA  00        BRK
0117DB  b08:$B7CB  40        RTI
0117DC  b08:$B7CC  80        .byte $80
0117DD  b08:$B7CD  70 81     BVS  $B750
0117DF  b08:$B7CF  00        BRK
0117E0  b08:$B7D0  82        .byte $82
0117E1  b08:$B7D1  30 83     BMI  $B756
0117E3  b08:$B7D3  C0 83     CPY  #$83
0117E5  b08:$B7D5  F0 84     BEQ  $B75B
0117E7  b08:$B7D7  80        .byte $80
0117E8  b08:$B7D8  85 B0     STA  $B0
0117EA  b08:$B7DA  86 40     STX  $40
0117EC  b08:$B7DC  87        .byte $87
0117ED  b08:$B7DD  70 88     BVS  $B767
0117EF  b08:$B7DF  00        BRK
0117F0  b08:$B7E0  89        .byte $89
0117F1  b08:$B7E1  30 8A     BMI  $B76D
0117F3  b08:$B7E3  C0 8A     CPY  #$8A
0117F5  b08:$B7E5  F0 8B     BEQ  $B772
0117F7  b08:$B7E7  80        .byte $80
0117F8  b08:$B7E8  8C B0 8D  STY  $8DB0
0117FB  b08:$B7EB  40        RTI
0117FC  b08:$B7EC  8E 70 8F  STX  $8F70
0117FF  b08:$B7EF  00        BRK
011800  b08:$B7F0  90 30     BCC  $B822
011802  b08:$B7F2  91 C0     STA  ($C0),Y
011804  b08:$B7F4  91 F0     STA  ($F0),Y
011806  b08:$B7F6  92        .byte $92
011807  b08:$B7F7  80        .byte $80
011808  b08:$B7F8  93        .byte $93
011809  b08:$B7F9  B0 94     BCS  $B78F
01180B  b08:$B7FB  40        RTI
01180C  b08:$B7FC  95 70     STA  $70,X
01180E  b08:$B7FE  96 00     STX  $00,Y
011810  b08:$B800  97        .byte $97
011811  b08:$B801  30 98     BMI  $B79B
011813  b08:$B803  C0 98     CPY  #$98
011815  b08:$B805  F0 99     BEQ  $B7A0
011817  b08:$B807  80        .byte $80
011818  b08:$B808  9A        TXS
011819  b08:$B809  B0 9B     BCS  $B7A6
01181B  b08:$B80B  A6 89     LDX  $89
01181D  b08:$B80D  D6 8A     DEC  $8A,X
01181F  b08:$B80F  66 8B     ROR  $8B
011821  b08:$B811  96 8C     STX  $8C,Y
011823  b08:$B813  26 8D     ROL  $8D
011825  b08:$B815  56 8E     LSR  $8E,X
011827  b08:$B817  E6 8E     INC  $8E
011829  b08:$B819  16 90     ASL  $90,X
01182B  b08:$B81B  A6 90     LDX  $90
01182D  b08:$B81D  D6 91     DEC  $91,X
01182F  b08:$B81F  66 92     ROR  $92
011831  b08:$B821  96 93     STX  $93,Y
011833  b08:$B823  26 94     ROL  $94
011835  b08:$B825  56 95     LSR  $95,X
011837  b08:$B827  E6 95     INC  $95
011839  b08:$B829  16 97     ASL  $97,X
01183B  b08:$B82B  A6 97     LDX  $97
01183D  b08:$B82D  D6 98     DEC  $98,X
01183F  b08:$B82F  66 99     ROR  $99
