; build_postbattle_roster: Side-marked active units then captured arrays, FE terminator
; Source semantics are direct Python; this is exact ROM provenance.
01B0F1 b13:$D0E1 A0 20          LDY  #$20
01B0F3 b13:$D0E3 A9 FF          LDA  #$FF
01B0F5 b13:$D0E5 99 80 05       STA  $0580,Y
01B0F8 b13:$D0E8 88             DEY
01B0F9 b13:$D0E9 10 FA          BPL  $D0E5
01B0FB b13:$D0EB A9 FF          LDA  #$FF
01B0FD b13:$D0ED 8D 0A 05       STA  $050A
01B100 b13:$D0F0 A0 1F          LDY  #$1F
01B102 b13:$D0F2 A9 FF          LDA  #$FF
01B104 b13:$D0F4 99 2C 04       STA  $042C,Y
01B107 b13:$D0F7 88             DEY
01B108 b13:$D0F8 10 FA          BPL  $D0F4
01B10A b13:$D0FA AD 0B 05       LDA  $050B
01B10D b13:$D0FD 29 10          AND  #$10
01B10F b13:$D0FF D0 33          BNE  $D134
01B111 b13:$D101 A0 00          LDY  #$00
01B113 b13:$D103 A2 00          LDX  #$00
01B115 b13:$D105 B9 28 06       LDA  $0628,Y
01B118 b13:$D108 29 80          AND  #$80
01B11A b13:$D10A D0 0B          BNE  $D117
01B11C b13:$D10C B9 64 06       LDA  $0664,Y
01B11F b13:$D10F C9 FF          CMP  #$FF
01B121 b13:$D111 F0 04          BEQ  $D117
01B123 b13:$D113 9D 2C 04       STA  $042C,X
01B126 b13:$D116 E8             INX
01B127 b13:$D117 C8             INY
01B128 b13:$D118 C0 14          CPY  #$14
01B12A b13:$D11A 90 E9          BCC  $D105
01B12C b13:$D11C A0 00          LDY  #$00
01B12E b13:$D11E B9 47 6F       LDA  $6F47,Y
01B131 b13:$D121 C9 FF          CMP  #$FF
01B133 b13:$D123 F0 04          BEQ  $D129
01B135 b13:$D125 9D 2C 04       STA  $042C,X
01B138 b13:$D128 E8             INX
01B139 b13:$D129 C8             INY
01B13A b13:$D12A C0 14          CPY  #$14
01B13C b13:$D12C 90 F0          BCC  $D11E
01B13E b13:$D12E A9 FE          LDA  #$FE
01B140 b13:$D130 9D 2C 04       STA  $042C,X
01B143 b13:$D133 60             RTS
01B144 b13:$D134 A0 00          LDY  #$00
01B146 b13:$D136 A2 00          LDX  #$00
01B148 b13:$D138 B9 28 06       LDA  $0628,Y
01B14B b13:$D13B 29 80          AND  #$80
01B14D b13:$D13D F0 0B          BEQ  $D14A
01B14F b13:$D13F B9 64 06       LDA  $0664,Y
01B152 b13:$D142 C9 FF          CMP  #$FF
01B154 b13:$D144 F0 04          BEQ  $D14A
01B156 b13:$D146 9D 2C 04       STA  $042C,X
01B159 b13:$D149 E8             INX
01B15A b13:$D14A C8             INY
01B15B b13:$D14B C0 14          CPY  #$14
01B15D b13:$D14D 90 E9          BCC  $D138
01B15F b13:$D14F A0 00          LDY  #$00
01B161 b13:$D151 B9 5B 6F       LDA  $6F5B,Y
01B164 b13:$D154 C9 FF          CMP  #$FF
01B166 b13:$D156 F0 04          BEQ  $D15C
01B168 b13:$D158 9D 2C 04       STA  $042C,X
01B16B b13:$D15B E8             INX
01B16C b13:$D15C C8             INY
01B16D b13:$D15D C0 14          CPY  #$14
01B16F b13:$D15F 90 F0          BCC  $D151
01B171 b13:$D161 A9 FE          LDA  #$FE
01B173 b13:$D163 9D 2C 04       STA  $042C,X
01B176 b13:$D166 60             RTS
