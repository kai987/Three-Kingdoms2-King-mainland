; damage_B188: physical bank 12, CPU $B188..$B1D4
; File offset $019198, exact byte SHA256 a5ce22017a7b7c9abd2ae410d8b04f51925e58c40a0c86a9ba615cbd13344e25
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B188 | $019198 | AC 0A 05 | LDY  $050A
$B18B | $01919B | B9 64 06 | LDA  $0664,Y
$B18E | $01919E | 20 D7 F2 | JSR  $F2D7
$B191 | $0191A1 | A0 01    | LDY  #$01
$B193 | $0191A3 | B1 00    | LDA  ($00),Y
$B195 | $0191A5 | 85 00    | STA  $00
$B197 | $0191A7 | A9 00    | LDA  #$00
$B199 | $0191A9 | 85 01    | STA  $01
$B19B | $0191AB | 85 02    | STA  $02
$B19D | $0191AD | A9 07    | LDA  #$07
$B19F | $0191AF | 20 62 E8 | JSR  $E862
$B1A2 | $0191B2 | 18       | CLC
$B1A3 | $0191B3 | 69 0E    | ADC  #$0E
$B1A5 | $0191B5 | 85 03    | STA  $03
$B1A7 | $0191B7 | 20 E9 EB | JSR  $EBE9
$B1AA | $0191BA | A5 06    | LDA  $06
$B1AC | $0191BC | 85 01    | STA  $01
$B1AE | $0191BE | A5 07    | LDA  $07
$B1B0 | $0191C0 | 85 02    | STA  $02
$B1B2 | $0191C2 | A9 0A    | LDA  #$0A
$B1B4 | $0191C4 | 85 03    | STA  $03
$B1B6 | $0191C6 | A9 00    | LDA  #$00
$B1B8 | $0191C8 | 85 04    | STA  $04
$B1BA | $0191CA | 20 7C EA | JSR  $EA7C
$B1BD | $0191CD | A5 02    | LDA  $02
$B1BF | $0191CF | 85 03    | STA  $03
$B1C1 | $0191D1 | A5 01    | LDA  $01
$B1C3 | $0191D3 | 85 02    | STA  $02
$B1C5 | $0191D5 | AC 09 05 | LDY  $0509
$B1C8 | $0191D8 | B9 64 06 | LDA  $0664,Y
$B1CB | $0191DB | 20 D7 F2 | JSR  $F2D7
$B1CE | $0191DE | 20 8B B6 | JSR  $B68B
$B1D1 | $0191E1 | EE 01 05 | INC  $0501
$B1D4 | $0191E4 | 60       | RTS
