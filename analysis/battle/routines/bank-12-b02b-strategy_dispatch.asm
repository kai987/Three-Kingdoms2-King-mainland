; strategy_dispatch: physical bank 12, CPU $B02B..$B061
; File offset $01903B, exact byte SHA256 ebe95363eda67700a67f3338b3c9ad74d9afa444e6cc437bdf4034e9ea55ebd7
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B02B | $01903B | A0 00    | LDY  #$00
$B02D | $01903D | A9 00    | LDA  #$00
$B02F | $01903F | 99 2C 04 | STA  $042C,Y
$B032 | $019042 | C8       | INY
$B033 | $019043 | C0 09    | CPY  #$09
$B035 | $019045 | 90 F8    | BCC  $B02F
$B037 | $019047 | 8D 44 05 | STA  $0544
$B03A | $01904A | AD 43 05 | LDA  $0543
$B03D | $01904D | 29 0F    | AND  #$0F
$B03F | $01904F | 20 DE EA | JSR  $EADE
; Sixteen strategy effect pointers, not instructions
$B042 | $019052 | .word $B062
$B044 | $019054 | .word $B0DD
$B046 | $019056 | .word $B155
$B048 | $019058 | .word $B17A
$B04A | $01905A | .word $B1D5
$B04C | $01905C | .word $B243
$B04E | $01905E | .word $B062
$B050 | $019060 | .word $B2CD
$B052 | $019062 | .word $B31C
$B054 | $019064 | .word $B3B6
$B056 | $019066 | .word $B3D0
$B058 | $019068 | .word $B42A
$B05A | $01906A | .word $B466
$B05C | $01906C | .word $B4B8
$B05E | $01906E | .word $B50C
$B060 | $019070 | .word $B5A6
