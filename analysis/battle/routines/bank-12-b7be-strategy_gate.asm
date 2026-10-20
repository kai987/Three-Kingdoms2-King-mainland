; strategy_gate: physical bank 12, CPU $B7BE..$B85F
; File offset $0197CE, exact byte SHA256 a37d1542333ebce30cf2fd281c1e1927a8773b294feb1b24ef2fbb5a71fd68d0
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B7BE | $0197CE | AC 09 05 | LDY  $0509
$B7C1 | $0197D1 | B9 64 06 | LDA  $0664,Y
$B7C4 | $0197D4 | 20 D7 F2 | JSR  $F2D7
$B7C7 | $0197D7 | A0 02    | LDY  #$02
$B7C9 | $0197D9 | B1 00    | LDA  ($00),Y
$B7CB | $0197DB | 85 10    | STA  $10
$B7CD | $0197DD | A0 0B    | LDY  #$0B
$B7CF | $0197DF | B1 00    | LDA  ($00),Y
$B7D1 | $0197E1 | 4A       | LSR  A
$B7D2 | $0197E2 | 4A       | LSR  A
$B7D3 | $0197E3 | 4A       | LSR  A
$B7D4 | $0197E4 | 4A       | LSR  A
$B7D5 | $0197E5 | 85 11    | STA  $11
$B7D7 | $0197E7 | AC 0A 05 | LDY  $050A
$B7DA | $0197EA | B9 64 06 | LDA  $0664,Y
$B7DD | $0197ED | 20 D7 F2 | JSR  $F2D7
$B7E0 | $0197F0 | A0 02    | LDY  #$02
$B7E2 | $0197F2 | B1 00    | LDA  ($00),Y
$B7E4 | $0197F4 | 85 12    | STA  $12
$B7E6 | $0197F6 | A0 0B    | LDY  #$0B
$B7E8 | $0197F8 | B1 00    | LDA  ($00),Y
$B7EA | $0197FA | 4A       | LSR  A
$B7EB | $0197FB | 4A       | LSR  A
$B7EC | $0197FC | 4A       | LSR  A
$B7ED | $0197FD | 4A       | LSR  A
$B7EE | $0197FE | 85 13    | STA  $13
$B7F0 | $019800 | A5 12    | LDA  $12
$B7F2 | $019802 | 38       | SEC
$B7F3 | $019803 | E5 10    | SBC  $10
$B7F5 | $019805 | B0 02    | BCS  $B7F9
$B7F7 | $019807 | A9 00    | LDA  #$00
$B7F9 | $019809 | 85 10    | STA  $10
$B7FB | $01980B | A5 13    | LDA  $13
$B7FD | $01980D | 38       | SEC
$B7FE | $01980E | E5 11    | SBC  $11
$B800 | $019810 | B0 02    | BCS  $B804
$B802 | $019812 | A9 00    | LDA  #$00
$B804 | $019814 | 0A       | ASL  A
$B805 | $019815 | 85 11    | STA  $11
$B807 | $019817 | 20 60 B8 | JSR  $B860
$B80A | $01981A | A8       | TAY
$B80B | $01981B | C0 06    | CPY  #$06
$B80D | $01981D | B0 47    | BCS  $B856
$B80F | $01981F | B9 5A B8 | LDA  $B85A,Y
$B812 | $019822 | 85 12    | STA  $12
$B814 | $019824 | A2 0A    | LDX  #$0A
$B816 | $019826 | AD 0F 05 | LDA  $050F
$B819 | $019829 | C9 03    | CMP  #$03
$B81B | $01982B | D0 0F    | BNE  $B82C
$B81D | $01982D | AD 02 6F | LDA  $6F02
$B820 | $019830 | C9 01    | CMP  #$01
$B822 | $019832 | F0 08    | BEQ  $B82C
$B824 | $019834 | A2 14    | LDX  #$14
$B826 | $019836 | C9 02    | CMP  #$02
$B828 | $019838 | F0 02    | BEQ  $B82C
$B82A | $01983A | A2 05    | LDX  #$05
$B82C | $01983C | 86 14    | STX  $14
$B82E | $01983E | A5 12    | LDA  $12
$B830 | $019840 | 18       | CLC
$B831 | $019841 | 65 10    | ADC  $10
$B833 | $019843 | 18       | CLC
$B834 | $019844 | 65 11    | ADC  $11
$B836 | $019846 | 18       | CLC
$B837 | $019847 | 65 14    | ADC  $14
$B839 | $019849 | 10 02    | BPL  $B83D
$B83B | $01984B | A9 00    | LDA  #$00
$B83D | $01984D | C9 5F    | CMP  #$5F
$B83F | $01984F | 90 02    | BCC  $B843
$B841 | $019851 | A9 5F    | LDA  #$5F
$B843 | $019853 | C9 05    | CMP  #$05
$B845 | $019855 | B0 02    | BCS  $B849
$B847 | $019857 | A9 05    | LDA  #$05
$B849 | $019859 | 85 00    | STA  $00
$B84B | $01985B | 20 7A E8 | JSR  $E87A
$B84E | $01985E | C9 64    | CMP  #$64
$B850 | $019860 | B0 F9    | BCS  $B84B
$B852 | $019862 | C5 00    | CMP  $00
$B854 | $019864 | 90 02    | BCC  $B858
$B856 | $019866 | 18       | CLC
$B857 | $019867 | 60       | RTS
$B858 | $019868 | 38       | SEC
$B859 | $019869 | 60       | RTS
; Distance correction bytes: 15,10,5,0,-5,-10
$B85A | $01986A | .byte $0F, $0A, $05, $00, $FB, $F6
