; conversion_gate: physical bank 12, CPU $B72B..$B7BD
; File offset $01973B, exact byte SHA256 41591b3d4972626bec287168922c37ae0e0e5288a21b5882e10e0d038a34986d
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B72B | $01973B | 20 60 B8 | JSR  $B860
$B72E | $01973E | C9 06    | CMP  #$06
$B730 | $019740 | 90 03    | BCC  $B735
$B732 | $019742 | 4C B6 B7 | JMP  $B7B6
$B735 | $019745 | AC 09 05 | LDY  $0509
$B738 | $019748 | B9 64 06 | LDA  $0664,Y
$B73B | $01974B | 20 D7 F2 | JSR  $F2D7
$B73E | $01974E | A2 00    | LDX  #$00
$B740 | $019750 | A0 0B    | LDY  #$0B
$B742 | $019752 | B1 00    | LDA  ($00),Y
$B744 | $019754 | 4A       | LSR  A
$B745 | $019755 | 4A       | LSR  A
$B746 | $019756 | 4A       | LSR  A
$B747 | $019757 | 4A       | LSR  A
$B748 | $019758 | 85 11    | STA  $11
$B74A | $01975A | A0 03    | LDY  #$03
$B74C | $01975C | B1 00    | LDA  ($00),Y
$B74E | $01975E | C9 1F    | CMP  #$1F
$B750 | $019760 | 90 0C    | BCC  $B75E
$B752 | $019762 | E8       | INX
$B753 | $019763 | C9 33    | CMP  #$33
$B755 | $019765 | 90 07    | BCC  $B75E
$B757 | $019767 | E8       | INX
$B758 | $019768 | C9 47    | CMP  #$47
$B75A | $01976A | 90 02    | BCC  $B75E
$B75C | $01976C | 18       | CLC
$B75D | $01976D | 60       | RTS
$B75E | $01976E | BD BA B7 | LDA  $B7BA,X
$B761 | $019771 | 85 10    | STA  $10
$B763 | $019773 | AC 0A 05 | LDY  $050A
$B766 | $019776 | B9 64 06 | LDA  $0664,Y
$B769 | $019779 | 20 D7 F2 | JSR  $F2D7
$B76C | $01977C | A5 00    | LDA  $00
$B76E | $01977E | 85 0A    | STA  $0A
$B770 | $019780 | A5 01    | LDA  $01
$B772 | $019782 | 85 0B    | STA  $0B
$B774 | $019784 | A0 0B    | LDY  #$0B
$B776 | $019786 | B1 0A    | LDA  ($0A),Y
$B778 | $019788 | 4A       | LSR  A
$B779 | $019789 | 4A       | LSR  A
$B77A | $01978A | 4A       | LSR  A
$B77B | $01978B | 4A       | LSR  A
$B77C | $01978C | 38       | SEC
$B77D | $01978D | E5 11    | SBC  $11
$B77F | $01978F | 10 02    | BPL  $B783
$B781 | $019791 | A9 00    | LDA  #$00
$B783 | $019793 | 0A       | ASL  A
$B784 | $019794 | 85 11    | STA  $11
$B786 | $019796 | A0 02    | LDY  #$02
$B788 | $019798 | B1 0A    | LDA  ($0A),Y
$B78A | $01979A | 85 01    | STA  $01
$B78C | $01979C | A0 04    | LDY  #$04
$B78E | $01979E | B1 0A    | LDA  ($0A),Y
$B790 | $0197A0 | 18       | CLC
$B791 | $0197A1 | 65 01    | ADC  $01
$B793 | $0197A3 | 85 01    | STA  $01
$B795 | $0197A5 | A9 00    | LDA  #$00
$B797 | $0197A7 | 85 02    | STA  $02
$B799 | $0197A9 | 85 04    | STA  $04
$B79B | $0197AB | A9 0A    | LDA  #$0A
$B79D | $0197AD | 85 03    | STA  $03
$B79F | $0197AF | 20 7C EA | JSR  $EA7C
$B7A2 | $0197B2 | A5 01    | LDA  $01
$B7A4 | $0197B4 | 18       | CLC
$B7A5 | $0197B5 | 65 10    | ADC  $10
$B7A7 | $0197B7 | 65 11    | ADC  $11
$B7A9 | $0197B9 | 85 00    | STA  $00
$B7AB | $0197BB | 20 7A E8 | JSR  $E87A
$B7AE | $0197BE | C9 64    | CMP  #$64
$B7B0 | $0197C0 | B0 F9    | BCS  $B7AB
$B7B2 | $0197C2 | C5 00    | CMP  $00
$B7B4 | $0197C4 | 90 02    | BCC  $B7B8
$B7B6 | $0197C6 | 18       | CLC
$B7B7 | $0197C7 | 60       | RTS
$B7B8 | $0197C8 | 38       | SEC
$B7B9 | $0197C9 | 60       | RTS
; Conversion base probabilities 60,30,10,5; normal threshold branches use first three
$B7BA | $0197CA | .byte $3C, $1E, $0A, $05
