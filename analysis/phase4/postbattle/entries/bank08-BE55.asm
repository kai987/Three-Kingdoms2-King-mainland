; prioritize_commander: Original side commander to first list entry
; Source semantics are direct Python; this is exact ROM provenance.
011E65 b08:$BE55 A0 00          LDY  #$00
011E67 b08:$BE57 AD 04 05       LDA  $0504
011E6A b08:$BE5A 10 02          BPL  $BE5E
011E6C b08:$BE5C A0 0A          LDY  #$0A
011E6E b08:$BE5E B9 64 06       LDA  $0664,Y
011E71 b08:$BE61 C9 FF          CMP  #$FF
011E73 b08:$BE63 D0 01          BNE  $BE66
011E75 b08:$BE65 60             RTS
011E76 b08:$BE66 8D 02 00       STA  $0002
011E79 b08:$BE69 A0 00          LDY  #$00
011E7B b08:$BE6B B9 A1 6F       LDA  $6FA1,Y
011E7E b08:$BE6E C9 FF          CMP  #$FF
011E80 b08:$BE70 F0 18          BEQ  $BE8A
011E82 b08:$BE72 CD 02 00       CMP  $0002
011E85 b08:$BE75 D0 13          BNE  $BE8A
011E87 b08:$BE77 AD A1 6F       LDA  $6FA1
011E8A b08:$BE7A 8D 03 00       STA  $0003
011E8D b08:$BE7D AD 02 00       LDA  $0002
011E90 b08:$BE80 8D A1 6F       STA  $6FA1
011E93 b08:$BE83 AD 03 00       LDA  $0003
011E96 b08:$BE86 99 A1 6F       STA  $6FA1,Y
011E99 b08:$BE89 60             RTS
011E9A b08:$BE8A C8             INY
011E9B b08:$BE8B C0 14          CPY  #$14
011E9D b08:$BE8D 90 DC          BCC  $BE6B
011E9F b08:$BE8F 60             RTS
