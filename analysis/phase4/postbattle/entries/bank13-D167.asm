; toggle_officer_selection: Capacity10 and prohibition on releasing the ruler
; Source semantics are direct Python; this is exact ROM provenance.
01B177 b13:$D167 A2 00          LDX  #$00
01B179 b13:$D169 A0 1F          LDY  #$1F
01B17B b13:$D16B B9 80 05       LDA  $0580,Y
01B17E b13:$D16E C9 FF          CMP  #$FF
01B180 b13:$D170 F0 01          BEQ  $D173
01B182 b13:$D172 E8             INX
01B183 b13:$D173 88             DEY
01B184 b13:$D174 10 F5          BPL  $D16B
01B186 b13:$D176 A5 81          LDA  $81
01B188 b13:$D178 29 01          AND  #$01
01B18A b13:$D17A F0 3F          BEQ  $D1BB
01B18C b13:$D17C AC 08 05       LDY  $0508
01B18F b13:$D17F CC 0A 05       CPY  $050A
01B192 b13:$D182 F0 37          BEQ  $D1BB
01B194 b13:$D184 B9 80 05       LDA  $0580,Y
01B197 b13:$D187 F0 2D          BEQ  $D1B6
01B199 b13:$D189 AD 40 05       LDA  $0540
01B19C b13:$D18C C9 1E          CMP  #$1E
01B19E b13:$D18E D0 0E          BNE  $D19E
01B1A0 b13:$D190 20 C3 D0       JSR  $D0C3
01B1A3 b13:$D193 AC 08 05       LDY  $0508
01B1A6 b13:$D196 D9 2C 04       CMP  $042C,Y
01B1A9 b13:$D199 F0 20          BEQ  $D1BB
01B1AB b13:$D19B 4C AD D1       JMP  $D1AD
01B1AE b13:$D19E 86 00          STX  $00
01B1B0 b13:$D1A0 AC 41 05       LDY  $0541
01B1B3 b13:$D1A3 A9 09          LDA  #$09
01B1B5 b13:$D1A5 38             SEC
01B1B6 b13:$D1A6 F9 50 05       SBC  $0550,Y
01B1B9 b13:$D1A9 C5 00          CMP  $00
01B1BB b13:$D1AB 90 0E          BCC  $D1BB
01B1BD b13:$D1AD AC 08 05       LDY  $0508
01B1C0 b13:$D1B0 A9 00          LDA  #$00
01B1C2 b13:$D1B2 99 80 05       STA  $0580,Y
01B1C5 b13:$D1B5 60             RTS
01B1C6 b13:$D1B6 A9 FF          LDA  #$FF
01B1C8 b13:$D1B8 99 80 05       STA  $0580,Y
01B1CB b13:$D1BB 60             RTS
