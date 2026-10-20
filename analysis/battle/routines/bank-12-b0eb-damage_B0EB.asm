; damage_B0EB: physical bank 12, CPU $B0EB..$B154
; File offset $0190FB, exact byte SHA256 895a03b701979a15a8d2424fc342a3e95eea0c6f58fbf89625e3071676927f1b
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B0EB | $0190FB | AC 0A 05 | LDY  $050A
$B0EE | $0190FE | B9 64 06 | LDA  $0664,Y
$B0F1 | $019101 | 20 D7 F2 | JSR  $F2D7
$B0F4 | $019104 | A0 0B    | LDY  #$0B
$B0F6 | $019106 | B1 00    | LDA  ($00),Y
$B0F8 | $019108 | 4A       | LSR  A
$B0F9 | $019109 | 4A       | LSR  A
$B0FA | $01910A | 4A       | LSR  A
$B0FB | $01910B | 4A       | LSR  A
$B0FC | $01910C | 48       | PHA
$B0FD | $01910D | A0 01    | LDY  #$01
$B0FF | $01910F | B1 00    | LDA  ($00),Y
$B101 | $019111 | 18       | CLC
$B102 | $019112 | A0 02    | LDY  #$02
$B104 | $019114 | 71 00    | ADC  ($00),Y
$B106 | $019116 | 85 01    | STA  $01
$B108 | $019118 | A9 00    | LDA  #$00
$B10A | $01911A | 85 02    | STA  $02
$B10C | $01911C | 85 04    | STA  $04
$B10E | $01911E | A9 0A    | LDA  #$0A
$B110 | $019120 | 85 03    | STA  $03
$B112 | $019122 | 20 7C EA | JSR  $EA7C
$B115 | $019125 | 68       | PLA
$B116 | $019126 | 18       | CLC
$B117 | $019127 | 65 01    | ADC  $01
$B119 | $019129 | 85 00    | STA  $00
$B11B | $01912B | A9 00    | LDA  #$00
$B11D | $01912D | 85 01    | STA  $01
$B11F | $01912F | 85 02    | STA  $02
$B121 | $019131 | A9 03    | LDA  #$03
$B123 | $019133 | 20 62 E8 | JSR  $E862
$B126 | $019136 | 18       | CLC
$B127 | $019137 | 69 05    | ADC  #$05
$B129 | $019139 | 85 03    | STA  $03
$B12B | $01913B | 20 E9 EB | JSR  $EBE9
$B12E | $01913E | A5 06    | LDA  $06
$B130 | $019140 | 85 01    | STA  $01
$B132 | $019142 | A5 07    | LDA  $07
$B134 | $019144 | 85 02    | STA  $02
$B136 | $019146 | A9 0A    | LDA  #$0A
$B138 | $019148 | 85 03    | STA  $03
$B13A | $01914A | A9 00    | LDA  #$00
$B13C | $01914C | 85 04    | STA  $04
$B13E | $01914E | 20 7C EA | JSR  $EA7C
$B141 | $019151 | A5 01    | LDA  $01
$B143 | $019153 | 85 02    | STA  $02
$B145 | $019155 | AC 09 05 | LDY  $0509
$B148 | $019158 | B9 64 06 | LDA  $0664,Y
$B14B | $01915B | 20 D7 F2 | JSR  $F2D7
$B14E | $01915E | 20 D8 B5 | JSR  $B5D8
$B151 | $019161 | EE 01 05 | INC  $0501
$B154 | $019164 | 60       | RTS
