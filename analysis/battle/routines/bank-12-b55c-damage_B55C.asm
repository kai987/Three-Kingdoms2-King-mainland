; damage_B55C: physical bank 12, CPU $B55C..$B5A5
; File offset $01956C, exact byte SHA256 681287b84a2bae3ac84a47350764185b7cb145964a3f2549131a5fb4ef9dee49
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B55C | $01956C | AC 0A 05 | LDY  $050A
$B55F | $01956F | B9 64 06 | LDA  $0664,Y
$B562 | $019572 | 20 D7 F2 | JSR  $F2D7
$B565 | $019575 | A9 06    | LDA  #$06
$B567 | $019577 | 20 62 E8 | JSR  $E862
$B56A | $01957A | 18       | CLC
$B56B | $01957B | 69 1E    | ADC  #$1E
$B56D | $01957D | 85 03    | STA  $03
$B56F | $01957F | A0 02    | LDY  #$02
$B571 | $019581 | B1 00    | LDA  ($00),Y
$B573 | $019583 | 85 00    | STA  $00
$B575 | $019585 | A9 00    | LDA  #$00
$B577 | $019587 | 85 01    | STA  $01
$B579 | $019589 | 85 02    | STA  $02
$B57B | $01958B | 20 E9 EB | JSR  $EBE9
$B57E | $01958E | A5 06    | LDA  $06
$B580 | $019590 | 85 01    | STA  $01
$B582 | $019592 | A5 07    | LDA  $07
$B584 | $019594 | 85 02    | STA  $02
$B586 | $019596 | A9 0A    | LDA  #$0A
$B588 | $019598 | 85 03    | STA  $03
$B58A | $01959A | A9 00    | LDA  #$00
$B58C | $01959C | 85 04    | STA  $04
$B58E | $01959E | 20 7C EA | JSR  $EA7C
$B591 | $0195A1 | A5 02    | LDA  $02
$B593 | $0195A3 | 85 03    | STA  $03
$B595 | $0195A5 | A5 01    | LDA  $01
$B597 | $0195A7 | 85 02    | STA  $02
$B599 | $0195A9 | AC 09 05 | LDY  $0509
$B59C | $0195AC | B9 64 06 | LDA  $0664,Y
$B59F | $0195AF | 20 D7 F2 | JSR  $F2D7
$B5A2 | $0195B2 | 20 8B B6 | JSR  $B68B
$B5A5 | $0195B5 | 60       | RTS
