; damage_B070: physical bank 12, CPU $B070..$B0DC
; File offset $019080, exact byte SHA256 984ac753e1b0504cd083af275e18e8d929699be374015de9efcbede9e0ed4aae
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B070 | $019080 | AC 0A 05 | LDY  $050A
$B073 | $019083 | B9 64 06 | LDA  $0664,Y
$B076 | $019086 | 20 D7 F2 | JSR  $F2D7
$B079 | $019089 | A0 0B    | LDY  #$0B
$B07B | $01908B | B1 00    | LDA  ($00),Y
$B07D | $01908D | 4A       | LSR  A
$B07E | $01908E | 4A       | LSR  A
$B07F | $01908F | 4A       | LSR  A
$B080 | $019090 | 4A       | LSR  A
$B081 | $019091 | 0A       | ASL  A
$B082 | $019092 | 85 02    | STA  $02
$B084 | $019094 | 0A       | ASL  A
$B085 | $019095 | 0A       | ASL  A
$B086 | $019096 | 18       | CLC
$B087 | $019097 | 65 02    | ADC  $02
$B089 | $019099 | 48       | PHA
$B08A | $01909A | A0 02    | LDY  #$02
$B08C | $01909C | B1 00    | LDA  ($00),Y
$B08E | $01909E | 85 00    | STA  $00
$B090 | $0190A0 | A9 00    | LDA  #$00
$B092 | $0190A2 | 85 01    | STA  $01
$B094 | $0190A4 | 85 02    | STA  $02
$B096 | $0190A6 | A9 05    | LDA  #$05
$B098 | $0190A8 | 20 62 E8 | JSR  $E862
$B09B | $0190AB | 18       | CLC
$B09C | $0190AC | 69 09    | ADC  #$09
$B09E | $0190AE | 85 03    | STA  $03
$B0A0 | $0190B0 | 20 E9 EB | JSR  $EBE9
$B0A3 | $0190B3 | A5 06    | LDA  $06
$B0A5 | $0190B5 | 85 01    | STA  $01
$B0A7 | $0190B7 | A5 07    | LDA  $07
$B0A9 | $0190B9 | 85 02    | STA  $02
$B0AB | $0190BB | A9 0A    | LDA  #$0A
$B0AD | $0190BD | 85 03    | STA  $03
$B0AF | $0190BF | A9 00    | LDA  #$00
$B0B1 | $0190C1 | 85 04    | STA  $04
$B0B3 | $0190C3 | 20 7C EA | JSR  $EA7C
$B0B6 | $0190C6 | 68       | PLA
$B0B7 | $0190C7 | 18       | CLC
$B0B8 | $0190C8 | 65 01    | ADC  $01
$B0BA | $0190CA | 85 02    | STA  $02
$B0BC | $0190CC | A9 00    | LDA  #$00
$B0BE | $0190CE | 85 03    | STA  $03
$B0C0 | $0190D0 | A5 02    | LDA  $02
$B0C2 | $0190D2 | 18       | CLC
$B0C3 | $0190D3 | 69 1E    | ADC  #$1E
$B0C5 | $0190D5 | 85 02    | STA  $02
$B0C7 | $0190D7 | A5 03    | LDA  $03
$B0C9 | $0190D9 | 69 00    | ADC  #$00
$B0CB | $0190DB | 85 03    | STA  $03
$B0CD | $0190DD | AC 09 05 | LDY  $0509
$B0D0 | $0190E0 | B9 64 06 | LDA  $0664,Y
$B0D3 | $0190E3 | 20 D7 F2 | JSR  $F2D7
$B0D6 | $0190E6 | 20 8B B6 | JSR  $B68B
$B0D9 | $0190E9 | EE 01 05 | INC  $0501
$B0DC | $0190EC | 60       | RTS
