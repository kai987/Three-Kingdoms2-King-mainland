; remove_inactive_unit_slot: Clear six active arrays,6FA1 and first matching attack cache
; Source semantics are direct Python; this is exact ROM provenance.
0136DD b09:$D6CD AC 00 00       LDY  $0000
0136E0 b09:$D6D0 A9 FF          LDA  #$FF
0136E2 b09:$D6D2 99 00 06       STA  $0600,Y
0136E5 b09:$D6D5 99 14 06       STA  $0614,Y
0136E8 b09:$D6D8 99 28 06       STA  $0628,Y
0136EB b09:$D6DB 99 3C 06       STA  $063C,Y
0136EE b09:$D6DE 99 50 06       STA  $0650,Y
0136F1 b09:$D6E1 99 64 06       STA  $0664,Y
0136F4 b09:$D6E4 99 A1 6F       STA  $6FA1,Y
0136F7 b09:$D6E7 A2 00          LDX  #$00
0136F9 b09:$D6E9 AD D8 04       LDA  $04D8
0136FC b09:$D6EC CD 00 00       CMP  $0000
0136FF b09:$D6EF F0 0B          BEQ  $D6FC
013701 b09:$D6F1 A2 04          LDX  #$04
013703 b09:$D6F3 AD DC 04       LDA  $04DC
013706 b09:$D6F6 CD 00 00       CMP  $0000
013709 b09:$D6F9 F0 01          BEQ  $D6FC
01370B b09:$D6FB 60             RTS
01370C b09:$D6FC 8A             TXA
01370D b09:$D6FD 18             CLC
01370E b09:$D6FE 69 04          ADC  #$04
013710 b09:$D700 8D 01 00       STA  $0001
013713 b09:$D703 A9 FF          LDA  #$FF
013715 b09:$D705 9D D8 04       STA  $04D8,X
013718 b09:$D708 E8             INX
013719 b09:$D709 EC 01 00       CPX  $0001
01371C b09:$D70C 90 F7          BCC  $D705
01371E b09:$D70E 60             RTS
