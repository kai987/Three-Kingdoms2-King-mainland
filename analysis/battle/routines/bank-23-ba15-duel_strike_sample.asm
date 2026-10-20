; duel_strike_sample: physical bank 23, CPU $BA15..$BA6C
; File offset $02FA25, exact byte SHA256 a3fc76f2af0b80a28a7ed0d01ae1b3ce0b99aef8daf5594e638fd9963ea7940c
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$BA15 | $02FA25 | 20 43 E8 | JSR  $E843
$BA18 | $02FA28 | 8D 10 00 | STA  $0010
$BA1B | $02FA2B | A0 00    | LDY  #$00
$BA1D | $02FA2D | AE AA 04 | LDX  $04AA
$BA20 | $02FA30 | BD AD 04 | LDA  $04AD,X
$BA23 | $02FA33 | CD 60 05 | CMP  $0560
$BA26 | $02FA36 | F0 02    | BEQ  $BA2A
$BA28 | $02FA38 | A0 01    | LDY  #$01
$BA2A | $02FA3A | B9 C1 04 | LDA  $04C1,Y
$BA2D | $02FA3D | 8D 01 00 | STA  $0001
$BA30 | $02FA40 | B9 70 05 | LDA  $0570,Y
$BA33 | $02FA43 | 18       | CLC
$BA34 | $02FA44 | 6D 01 00 | ADC  $0001
$BA37 | $02FA47 | 4A       | LSR  A
$BA38 | $02FA48 | 8D 01 00 | STA  $0001
$BA3B | $02FA4B | 98       | TYA
$BA3C | $02FA4C | 49 01    | EOR  #$01
$BA3E | $02FA4E | A8       | TAY
$BA3F | $02FA4F | B9 6E 05 | LDA  $056E,Y
$BA42 | $02FA52 | 8D 02 00 | STA  $0002
$BA45 | $02FA55 | AD 01 00 | LDA  $0001
$BA48 | $02FA58 | 38       | SEC
$BA49 | $02FA59 | ED 02 00 | SBC  $0002
$BA4C | $02FA5C | 8D 01 00 | STA  $0001
$BA4F | $02FA5F | 20 7A E8 | JSR  $E87A
$BA52 | $02FA62 | 29 0F    | AND  #$0F
$BA54 | $02FA64 | C9 0B    | CMP  #$0B
$BA56 | $02FA66 | B0 F7    | BCS  $BA4F
$BA58 | $02FA68 | 38       | SEC
$BA59 | $02FA69 | E9 05    | SBC  #$05
$BA5B | $02FA6B | 8D 02 00 | STA  $0002
$BA5E | $02FA6E | AD 01 00 | LDA  $0001
$BA61 | $02FA71 | 18       | CLC
$BA62 | $02FA72 | 6D 02 00 | ADC  $0002
$BA65 | $02FA75 | 10 02    | BPL  $BA69
$BA67 | $02FA77 | A9 00    | LDA  #$00
$BA69 | $02FA79 | 8D 01 00 | STA  $0001
$BA6C | $02FA7C | 60       | RTS
