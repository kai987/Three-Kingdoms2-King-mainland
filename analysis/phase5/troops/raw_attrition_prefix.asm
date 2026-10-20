;Full-word subtraction with highbyte BPL clipping; later slot loop excluded.
;Exact bounded entry/prefix; no linear-data-as-code claim.
012E85 b09:$CE75 A0 08      LDY  #$08
012E87 b09:$CE77 B1 00      LDA  ($00),Y
012E89 b09:$CE79 38         SEC
012E8A b09:$CE7A ED 02 00   SBC  $0002
012E8D b09:$CE7D 8D 02 00   STA  $0002
012E90 b09:$CE80 C8         INY
012E91 b09:$CE81 B1 00      LDA  ($00),Y
012E93 b09:$CE83 E9 00      SBC  #$00
012E95 b09:$CE85 10 05      BPL  $CE8C
012E97 b09:$CE87 A9 00      LDA  #$00
012E99 b09:$CE89 8D 02 00   STA  $0002
012E9C b09:$CE8C 91 00      STA  ($00),Y
012E9E b09:$CE8E 88         DEY
012E9F b09:$CE8F AD 02 00   LDA  $0002
012EA2 b09:$CE92 91 00      STA  ($00),Y
