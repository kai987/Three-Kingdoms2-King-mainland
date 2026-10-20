; experience_from_accumulated_loss: physical bank 15, CPU $D7FB..$D8AF
; File offset $01F80B, exact byte SHA256 7847294d5611bf7c188c21545480658e925c5130c3550a47e4f7fcf6b25f37ae
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$D7FB | $01F80B | AD 0A 00 | LDA  $000A
$D7FE | $01F80E | 20 D7 F2 | JSR  $F2D7
$D801 | $01F811 | 4E 0C 00 | LSR  $000C
$D804 | $01F814 | 6E 0B 00 | ROR  $000B
$D807 | $01F817 | A0 06    | LDY  #$06
$D809 | $01F819 | B1 00    | LDA  ($00),Y
$D80B | $01F81B | 18       | CLC
$D80C | $01F81C | 6D 0B 00 | ADC  $000B
$D80F | $01F81F | 8D 0D 00 | STA  $000D
$D812 | $01F822 | 91 00    | STA  ($00),Y
$D814 | $01F824 | C8       | INY
$D815 | $01F825 | B1 00    | LDA  ($00),Y
$D817 | $01F827 | 6D 0C 00 | ADC  $000C
$D81A | $01F82A | 8D 0E 00 | STA  $000E
$D81D | $01F82D | 91 00    | STA  ($00),Y
$D81F | $01F82F | A0 06    | LDY  #$06
$D821 | $01F831 | B1 00    | LDA  ($00),Y
$D823 | $01F833 | 38       | SEC
$D824 | $01F834 | E9 4F    | SBC  #$4F
$D826 | $01F836 | C8       | INY
$D827 | $01F837 | B1 00    | LDA  ($00),Y
$D829 | $01F839 | E9 C3    | SBC  #$C3
$D82B | $01F83B | 90 0B    | BCC  $D838
$D82D | $01F83D | A0 06    | LDY  #$06
$D82F | $01F83F | A9 4F    | LDA  #$4F
$D831 | $01F841 | 91 00    | STA  ($00),Y
$D833 | $01F843 | C8       | INY
$D834 | $01F844 | A9 C3    | LDA  #$C3
$D836 | $01F846 | 91 00    | STA  ($00),Y
$D838 | $01F848 | A0 0B    | LDY  #$0B
$D83A | $01F84A | B1 00    | LDA  ($00),Y
$D83C | $01F84C | 29 F0    | AND  #$F0
$D83E | $01F84E | 4A       | LSR  A
$D83F | $01F84F | 4A       | LSR  A
$D840 | $01F850 | 4A       | LSR  A
$D841 | $01F851 | C9 0E    | CMP  #$0E
$D843 | $01F853 | B0 10    | BCS  $D855
$D845 | $01F855 | A8       | TAY
$D846 | $01F856 | AD 0D 00 | LDA  $000D
$D849 | $01F859 | 38       | SEC
$D84A | $01F85A | F9 5B D8 | SBC  $D85B,Y
$D84D | $01F85D | AD 0E 00 | LDA  $000E
$D850 | $01F860 | F9 5C D8 | SBC  $D85C,Y
$D853 | $01F863 | B0 14    | BCS  $D869
$D855 | $01F865 | A9 00    | LDA  #$00
$D857 | $01F867 | 8D 0F 00 | STA  $000F
$D85A | $01F86A | 60       | RTS
; Seven experience thresholds, not instructions
$D85B | $01F86B | .word $03E8
$D85D | $01F86D | .word $07D0
$D85F | $01F86F | .word $0DAC
$D861 | $01F871 | .word $1388
$D863 | $01F873 | .word $1D4C
$D865 | $01F875 | .word $2710
$D867 | $01F877 | .word $3A98
$D869 | $01F879 | 98       | TYA
$D86A | $01F87A | 4A       | LSR  A
$D86B | $01F87B | 18       | CLC
$D86C | $01F87C | 69 01    | ADC  #$01
$D86E | $01F87E | 0A       | ASL  A
$D86F | $01F87F | 0A       | ASL  A
$D870 | $01F880 | 0A       | ASL  A
$D871 | $01F881 | 0A       | ASL  A
$D872 | $01F882 | 8D 0F 00 | STA  $000F
$D875 | $01F885 | A0 0B    | LDY  #$0B
$D877 | $01F887 | B1 00    | LDA  ($00),Y
$D879 | $01F889 | 29 F0    | AND  #$F0
$D87B | $01F88B | CD 0F 00 | CMP  $000F
$D87E | $01F88E | B0 D5    | BCS  $D855
$D880 | $01F890 | A0 0B    | LDY  #$0B
$D882 | $01F892 | B1 00    | LDA  ($00),Y
$D884 | $01F894 | 29 0F    | AND  #$0F
$D886 | $01F896 | 0D 0F 00 | ORA  $000F
$D889 | $01F899 | 91 00    | STA  ($00),Y
$D88B | $01F89B | A0 01    | LDY  #$01
$D88D | $01F89D | B1 00    | LDA  ($00),Y
$D88F | $01F89F | A0 06    | LDY  #$06
$D891 | $01F8A1 | C9 33    | CMP  #$33
$D893 | $01F8A3 | 90 12    | BCC  $D8A7
$D895 | $01F8A5 | A0 05    | LDY  #$05
$D897 | $01F8A7 | C9 47    | CMP  #$47
$D899 | $01F8A9 | 90 0C    | BCC  $D8A7
$D89B | $01F8AB | A0 04    | LDY  #$04
$D89D | $01F8AD | C9 51    | CMP  #$51
$D89F | $01F8AF | 90 06    | BCC  $D8A7
$D8A1 | $01F8B1 | A0 02    | LDY  #$02
$D8A3 | $01F8B3 | C9 5A    | CMP  #$5A
$D8A5 | $01F8B5 | B0 08    | BCS  $D8AF
$D8A7 | $01F8B7 | 98       | TYA
$D8A8 | $01F8B8 | A0 01    | LDY  #$01
$D8AA | $01F8BA | 18       | CLC
$D8AB | $01F8BB | 71 00    | ADC  ($00),Y
$D8AD | $01F8BD | 91 00    | STA  ($00),Y
$D8AF | $01F8BF | 60       | RTS
