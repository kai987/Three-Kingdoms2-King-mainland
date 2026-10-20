; duel_health_strike: physical bank 23, CPU $BB5B..$BB92
; File offset $02FB6B, exact byte SHA256 c832b71ac2e3aa36f08b03a6dec26c55c8cd8236ee69d6ba06276f820c321354
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$BB5B | $02FB6B | A9 0A    | LDA  #$0A
$BB5D | $02FB6D | 20 62 E8 | JSR  $E862
$BB60 | $02FB70 | 18       | CLC
$BB61 | $02FB71 | 69 05    | ADC  #$05
$BB63 | $02FB73 | 8D 2F 04 | STA  $042F
$BB66 | $02FB76 | A9 00    | LDA  #$00
$BB68 | $02FB78 | 8D 30 04 | STA  $0430
$BB6B | $02FB7B | 8D 31 04 | STA  $0431
$BB6E | $02FB7E | AD AA 04 | LDA  $04AA
$BB71 | $02FB81 | 49 01    | EOR  #$01
$BB73 | $02FB83 | A8       | TAY
$BB74 | $02FB84 | B9 AD 04 | LDA  $04AD,Y
$BB77 | $02FB87 | 8D 2C 04 | STA  $042C
$BB7A | $02FB8A | 20 D7 F2 | JSR  $F2D7
$BB7D | $02FB8D | A0 00    | LDY  #$00
$BB7F | $02FB8F | B1 00    | LDA  ($00),Y
$BB81 | $02FB91 | 38       | SEC
$BB82 | $02FB92 | ED 2F 04 | SBC  $042F
$BB85 | $02FB95 | 10 02    | BPL  $BB89
$BB87 | $02FB97 | A9 00    | LDA  #$00
$BB89 | $02FB99 | 91 00    | STA  ($00),Y
$BB8B | $02FB9B | EE A9 04 | INC  $04A9
$BB8E | $02FB9E | A9 3D    | LDA  #$3D
$BB90 | $02FBA0 | 4C 8B F2 | JMP  $F28B
