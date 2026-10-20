; duel_attack_parameters: physical bank 15, CPU $C991..$CA3E
; File offset $01E9A1, exact byte SHA256 05c7a073d08b6f76c6a3832a72c8eeae61698c9bd99b1e049e8d5b9f9e2a67cf
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$C991 | $01E9A1 | A0 0A    | LDY  #$0A
$C993 | $01E9A3 | B1 00    | LDA  ($00),Y
$C995 | $01E9A5 | 48       | PHA
$C996 | $01E9A6 | A0 01    | LDY  #$01
$C998 | $01E9A8 | B1 00    | LDA  ($00),Y
$C99A | $01E9AA | A0 2D    | LDY  #$2D
$C99C | $01E9AC | C9 32    | CMP  #$32
$C99E | $01E9AE | 90 20    | BCC  $C9C0
$C9A0 | $01E9B0 | A0 2D    | LDY  #$2D
$C9A2 | $01E9B2 | C9 41    | CMP  #$41
$C9A4 | $01E9B4 | 90 1A    | BCC  $C9C0
$C9A6 | $01E9B6 | A0 32    | LDY  #$32
$C9A8 | $01E9B8 | C9 50    | CMP  #$50
$C9AA | $01E9BA | 90 14    | BCC  $C9C0
$C9AC | $01E9BC | A0 37    | LDY  #$37
$C9AE | $01E9BE | C9 57    | CMP  #$57
$C9B0 | $01E9C0 | 90 0E    | BCC  $C9C0
$C9B2 | $01E9C2 | A0 3C    | LDY  #$3C
$C9B4 | $01E9C4 | C9 5C    | CMP  #$5C
$C9B6 | $01E9C6 | 90 08    | BCC  $C9C0
$C9B8 | $01E9C8 | A0 41    | LDY  #$41
$C9BA | $01E9CA | C9 61    | CMP  #$61
$C9BC | $01E9CC | 90 02    | BCC  $C9C0
$C9BE | $01E9CE | A0 46    | LDY  #$46
$C9C0 | $01E9D0 | 8C 03 00 | STY  $0003
$C9C3 | $01E9D3 | 8D 00 00 | STA  $0000
$C9C6 | $01E9D6 | A9 00    | LDA  #$00
$C9C8 | $01E9D8 | 8D 01 00 | STA  $0001
$C9CB | $01E9DB | 8D 02 00 | STA  $0002
$C9CE | $01E9DE | 20 E9 EB | JSR  $EBE9
$C9D1 | $01E9E1 | AD 06 00 | LDA  $0006
$C9D4 | $01E9E4 | 8D 01 00 | STA  $0001
$C9D7 | $01E9E7 | AD 07 00 | LDA  $0007
$C9DA | $01E9EA | 8D 02 00 | STA  $0002
$C9DD | $01E9ED | A9 64    | LDA  #$64
$C9DF | $01E9EF | 8D 03 00 | STA  $0003
$C9E2 | $01E9F2 | A9 00    | LDA  #$00
$C9E4 | $01E9F4 | 8D 04 00 | STA  $0004
$C9E7 | $01E9F7 | 20 7C EA | JSR  $EA7C
$C9EA | $01E9FA | 20 7A E8 | JSR  $E87A
$C9ED | $01E9FD | 29 0F    | AND  #$0F
$C9EF | $01E9FF | C9 09    | CMP  #$09
$C9F1 | $01EA01 | B0 F7    | BCS  $C9EA
$C9F3 | $01EA03 | 8D 02 00 | STA  $0002
$C9F6 | $01EA06 | AD 01 00 | LDA  $0001
$C9F9 | $01EA09 | 18       | CLC
$C9FA | $01EA0A | 69 09    | ADC  #$09
$C9FC | $01EA0C | 38       | SEC
$C9FD | $01EA0D | ED 02 00 | SBC  $0002
$CA00 | $01EA10 | B0 02    | BCS  $CA04
$CA02 | $01EA12 | A9 01    | LDA  #$01
$CA04 | $01EA14 | 8D 01 00 | STA  $0001
$CA07 | $01EA17 | 68       | PLA
$CA08 | $01EA18 | 48       | PHA
$CA09 | $01EA19 | 29 1F    | AND  #$1F
$CA0B | $01EA1B | A8       | TAY
$CA0C | $01EA1C | B9 1F CA | LDA  $CA1F,Y
$CA0F | $01EA1F | A8       | TAY
$CA10 | $01EA20 | 68       | PLA
$CA11 | $01EA21 | 4A       | LSR  A
$CA12 | $01EA22 | 4A       | LSR  A
$CA13 | $01EA23 | 4A       | LSR  A
$CA14 | $01EA24 | 4A       | LSR  A
$CA15 | $01EA25 | 4A       | LSR  A
$CA16 | $01EA26 | AA       | TAX
$CA17 | $01EA27 | BD 37 CA | LDA  $CA37,X
$CA1A | $01EA2A | AA       | TAX
$CA1B | $01EA2B | AD 01 00 | LDA  $0001
$CA1E | $01EA2E | 60       | RTS
; Duel weapon attack bonuses followed by eight armor defense modifiers
$CA1F | $01EA2F | .byte $03, $04, $07, $09, $0D, $0F, $10, $11, $04, $05, $08, $0A, $0C, $0B, $11, $13, $05, $06, $07, $0A, $0B, $10, $12, $14, $02, $03, $05, $07, $08, $0A, $0B, $0C
