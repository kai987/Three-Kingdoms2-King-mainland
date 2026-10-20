; damage_B4C6: physical bank 12, CPU $B4C6..$B50B
; File offset $0194D6, exact byte SHA256 a592c2a1f96b2c469265bc8a53e392107c625b11f3b55000d2dff5589bc96496
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B4C6 | $0194D6 | AC 0A 05 | LDY  $050A
$B4C9 | $0194D9 | B9 64 06 | LDA  $0664,Y
$B4CC | $0194DC | 20 D7 F2 | JSR  $F2D7
$B4CF | $0194DF | A9 00    | LDA  #$00
$B4D1 | $0194E1 | 85 02    | STA  $02
$B4D3 | $0194E3 | 85 03    | STA  $03
$B4D5 | $0194E5 | 20 7A E8 | JSR  $E87A
$B4D8 | $0194E8 | C9 C8    | CMP  #$C8
$B4DA | $0194EA | B0 F9    | BCS  $B4D5
$B4DC | $0194EC | 18       | CLC
$B4DD | $0194ED | 69 96    | ADC  #$96
$B4DF | $0194EF | 85 02    | STA  $02
$B4E1 | $0194F1 | A5 03    | LDA  $03
$B4E3 | $0194F3 | 69 00    | ADC  #$00
$B4E5 | $0194F5 | 85 03    | STA  $03
$B4E7 | $0194F7 | A0 01    | LDY  #$01
$B4E9 | $0194F9 | B1 00    | LDA  ($00),Y
$B4EB | $0194FB | 18       | CLC
$B4EC | $0194FC | A0 02    | LDY  #$02
$B4EE | $0194FE | 71 00    | ADC  ($00),Y
$B4F0 | $019500 | 4A       | LSR  A
$B4F1 | $019501 | 18       | CLC
$B4F2 | $019502 | 65 02    | ADC  $02
$B4F4 | $019504 | 85 02    | STA  $02
$B4F6 | $019506 | A5 03    | LDA  $03
$B4F8 | $019508 | 69 00    | ADC  #$00
$B4FA | $01950A | 85 03    | STA  $03
$B4FC | $01950C | AC 09 05 | LDY  $0509
$B4FF | $01950F | B9 64 06 | LDA  $0664,Y
$B502 | $019512 | 20 D7 F2 | JSR  $F2D7
$B505 | $019515 | 20 8B B6 | JSR  $B68B
$B508 | $019518 | EE 01 05 | INC  $0501
$B50B | $01951B | 60       | RTS
