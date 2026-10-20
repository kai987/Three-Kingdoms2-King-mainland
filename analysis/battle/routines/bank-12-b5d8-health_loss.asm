; health_loss: physical bank 12, CPU $B5D8..$B642
; File offset $0195E8, exact byte SHA256 228e3e8ebd945cebe61a58af3262003406d8e5fbf47da29304bb7e599fa634e7
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B5D8 | $0195E8 | A0 00    | LDY  #$00
$B5DA | $0195EA | B1 00    | LDA  ($00),Y
$B5DC | $0195EC | 85 04    | STA  $04
$B5DE | $0195EE | 38       | SEC
$B5DF | $0195EF | E5 02    | SBC  $02
$B5E1 | $0195F1 | 85 06    | STA  $06
$B5E3 | $0195F3 | B0 08    | BCS  $B5ED
$B5E5 | $0195F5 | A5 04    | LDA  $04
$B5E7 | $0195F7 | 85 02    | STA  $02
$B5E9 | $0195F9 | A9 00    | LDA  #$00
$B5EB | $0195FB | 85 06    | STA  $06
$B5ED | $0195FD | A0 00    | LDY  #$00
$B5EF | $0195FF | A5 06    | LDA  $06
$B5F1 | $019601 | 91 00    | STA  ($00),Y
$B5F3 | $019603 | A5 02    | LDA  $02
$B5F5 | $019605 | 8D 2F 04 | STA  $042F
$B5F8 | $019608 | A9 00    | LDA  #$00
$B5FA | $01960A | 8D 30 04 | STA  $0430
$B5FD | $01960D | 8D 31 04 | STA  $0431
$B600 | $019610 | A9 FF    | LDA  #$FF
$B602 | $019612 | 8D 32 04 | STA  $0432
$B605 | $019615 | A5 06    | LDA  $06
$B607 | $019617 | D0 39    | BNE  $B642
$B609 | $019619 | A0 0B    | LDY  #$0B
$B60B | $01961B | B1 00    | LDA  ($00),Y
$B60D | $01961D | 09 03    | ORA  #$03
$B60F | $01961F | 91 00    | STA  ($00),Y
$B611 | $019621 | A9 00    | LDA  #$00
$B613 | $019623 | 85 12    | STA  $12
$B615 | $019625 | 20 CC D6 | JSR  $D6CC
$B618 | $019628 | AC 0A 05 | LDY  $050A
$B61B | $01962B | B9 64 06 | LDA  $0664,Y
$B61E | $01962E | 85 0A    | STA  $0A
$B620 | $019630 | AC 09 05 | LDY  $0509
$B623 | $019633 | B9 64 06 | LDA  $0664,Y
$B626 | $019636 | 85 0B    | STA  $0B
$B628 | $019638 | A0 2E    | LDY  #$2E
$B62A | $01963A | 20 07 EE | JSR  $EE07
$B62D | $01963D | .word $A009 ; EE07 inline far-call target
$B62F | $01963F | AC 09 05 | LDY  $0509
$B632 | $019642 | B9 64 06 | LDA  $0664,Y
$B635 | $019645 | 8D 32 04 | STA  $0432
$B638 | $019648 | 8C 00 00 | STY  $0000
$B63B | $01964B | A0 28    | LDY  #$28
$B63D | $01964D | 20 07 EE | JSR  $EE07
$B640 | $019650 | .word $A02A ; EE07 inline far-call target
$B642 | $019652 | 60       | RTS
