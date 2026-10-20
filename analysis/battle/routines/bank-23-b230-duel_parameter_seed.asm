; duel_parameter_seed: physical bank 23, CPU $B230..$B2DF
; File offset $02F240, exact byte SHA256 bd9368c771af372cdd9b3fda33fdc764cbcd794ecc4ac7e83935e49599c90035
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B230 | $02F240 | A2 00    | LDX  #$00
$B232 | $02F242 | BD AD 04 | LDA  $04AD,X
$B235 | $02F245 | 20 D7 F2 | JSR  $F2D7
$B238 | $02F248 | A0 0A    | LDY  #$0A
$B23A | $02F24A | B1 00    | LDA  ($00),Y
$B23C | $02F24C | 8D 10 00 | STA  $0010
$B23F | $02F24F | 4A       | LSR  A
$B240 | $02F250 | 4A       | LSR  A
$B241 | $02F251 | 4A       | LSR  A
$B242 | $02F252 | 4A       | LSR  A
$B243 | $02F253 | 4A       | LSR  A
$B244 | $02F254 | 18       | CLC
$B245 | $02F255 | 69 18    | ADC  #$18
$B247 | $02F257 | 8D 11 00 | STA  $0011
$B24A | $02F25A | AD 10 00 | LDA  $0010
$B24D | $02F25D | 29 1F    | AND  #$1F
$B24F | $02F25F | 8D 10 00 | STA  $0010
$B252 | $02F262 | A8       | TAY
$B253 | $02F263 | B9 C0 B2 | LDA  $B2C0,Y
$B256 | $02F266 | 8D 10 00 | STA  $0010
$B259 | $02F269 | AC 11 00 | LDY  $0011
$B25C | $02F26C | B9 C0 B2 | LDA  $B2C0,Y
$B25F | $02F26F | 18       | CLC
$B260 | $02F270 | 6D 10 00 | ADC  $0010
$B263 | $02F273 | 8D 10 00 | STA  $0010
$B266 | $02F276 | A0 00    | LDY  #$00
$B268 | $02F278 | B1 00    | LDA  ($00),Y
$B26A | $02F27A | 8D 02 00 | STA  $0002
$B26D | $02F27D | A0 01    | LDY  #$01
$B26F | $02F27F | B1 00    | LDA  ($00),Y
$B271 | $02F281 | 18       | CLC
$B272 | $02F282 | 6D 02 00 | ADC  $0002
$B275 | $02F285 | 8D 01 00 | STA  $0001
$B278 | $02F288 | A9 00    | LDA  #$00
$B27A | $02F28A | 8D 02 00 | STA  $0002
$B27D | $02F28D | 8D 04 00 | STA  $0004
$B280 | $02F290 | A9 0A    | LDA  #$0A
$B282 | $02F292 | 8D 03 00 | STA  $0003
$B285 | $02F295 | 20 7C EA | JSR  $EA7C
$B288 | $02F298 | AD 01 00 | LDA  $0001
$B28B | $02F29B | 18       | CLC
$B28C | $02F29C | 69 14    | ADC  #$14
$B28E | $02F29E | 38       | SEC
$B28F | $02F29F | ED 10 00 | SBC  $0010
$B292 | $02F2A2 | 9D B3 04 | STA  $04B3,X
$B295 | $02F2A5 | 20 7A E8 | JSR  $E87A
$B298 | $02F2A8 | 29 0F    | AND  #$0F
$B29A | $02F2AA | C9 0B    | CMP  #$0B
$B29C | $02F2AC | B0 F7    | BCS  $B295
$B29E | $02F2AE | 7D B3 04 | ADC  $04B3,X
$B2A1 | $02F2B1 | 9D BD 04 | STA  $04BD,X
$B2A4 | $02F2B4 | E8       | INX
$B2A5 | $02F2B5 | E0 02    | CPX  #$02
$B2A7 | $02F2B7 | D0 89    | BNE  $B232
$B2A9 | $02F2B9 | A2 00    | LDX  #$00
$B2AB | $02F2BB | AD BD 04 | LDA  $04BD
$B2AE | $02F2BE | CD BE 04 | CMP  $04BE
$B2B1 | $02F2C1 | B0 01    | BCS  $B2B4
$B2B3 | $02F2C3 | E8       | INX
$B2B4 | $02F2C4 | 8E AA 04 | STX  $04AA
$B2B7 | $02F2C7 | A9 00    | LDA  #$00
$B2B9 | $02F2C9 | 8D C0 04 | STA  $04C0
$B2BC | $02F2CC | EE A9 04 | INC  $04A9
$B2BF | $02F2CF | 60       | RTS
; Equipment correction lookup: 24+8 entries
$B2C0 | $02F2D0 | .byte $04, $03, $05, $08, $09, $06, $07, $04, $04, $06, $07, $08, $07, $06, $08, $0A, $04, $05, $06, $08, $07, $08, $06, $0A, $01, $02, $04, $06, $05, $0A, $03, $07
