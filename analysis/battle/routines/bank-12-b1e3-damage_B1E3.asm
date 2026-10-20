; damage_B1E3: physical bank 12, CPU $B1E3..$B242
; File offset $0191F3, exact byte SHA256 0994b51bf3e9270a344db5e2fbd56065587d6e1b35353fd46cdf9fe58a8983b9
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B1E3 | $0191F3 | AC 0A 05 | LDY  $050A
$B1E6 | $0191F6 | B9 64 06 | LDA  $0664,Y
$B1E9 | $0191F9 | 20 D7 F2 | JSR  $F2D7
$B1EC | $0191FC | A0 0B    | LDY  #$0B
$B1EE | $0191FE | B1 00    | LDA  ($00),Y
$B1F0 | $019200 | 4A       | LSR  A
$B1F1 | $019201 | 4A       | LSR  A
$B1F2 | $019202 | 4A       | LSR  A
$B1F3 | $019203 | 4A       | LSR  A
$B1F4 | $019204 | 48       | PHA
$B1F5 | $019205 | A0 02    | LDY  #$02
$B1F7 | $019207 | B1 00    | LDA  ($00),Y
$B1F9 | $019209 | 85 00    | STA  $00
$B1FB | $01920B | A9 00    | LDA  #$00
$B1FD | $01920D | 85 01    | STA  $01
$B1FF | $01920F | 85 02    | STA  $02
$B201 | $019211 | A9 07    | LDA  #$07
$B203 | $019213 | 20 62 E8 | JSR  $E862
$B206 | $019216 | 18       | CLC
$B207 | $019217 | 69 14    | ADC  #$14
$B209 | $019219 | 85 03    | STA  $03
$B20B | $01921B | 20 E9 EB | JSR  $EBE9
$B20E | $01921E | A5 06    | LDA  $06
$B210 | $019220 | 85 01    | STA  $01
$B212 | $019222 | A5 07    | LDA  $07
$B214 | $019224 | 85 02    | STA  $02
$B216 | $019226 | A9 0A    | LDA  #$0A
$B218 | $019228 | 85 03    | STA  $03
$B21A | $01922A | A9 00    | LDA  #$00
$B21C | $01922C | 85 04    | STA  $04
$B21E | $01922E | 20 7C EA | JSR  $EA7C
$B221 | $019231 | 68       | PLA
$B222 | $019232 | 18       | CLC
$B223 | $019233 | 69 07    | ADC  #$07
$B225 | $019235 | 65 01    | ADC  $01
$B227 | $019237 | 85 01    | STA  $01
$B229 | $019239 | A5 02    | LDA  $02
$B22B | $01923B | 69 00    | ADC  #$00
$B22D | $01923D | 85 03    | STA  $03
$B22F | $01923F | A5 01    | LDA  $01
$B231 | $019241 | 85 02    | STA  $02
$B233 | $019243 | AC 09 05 | LDY  $0509
$B236 | $019246 | B9 64 06 | LDA  $0664,Y
$B239 | $019249 | 20 D7 F2 | JSR  $F2D7
$B23C | $01924C | 20 8B B6 | JSR  $B68B
$B23F | $01924F | EE 01 05 | INC  $0501
$B242 | $019252 | 60       | RTS
