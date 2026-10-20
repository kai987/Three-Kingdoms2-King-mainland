; grid_distance: physical bank 12, CPU $B860..$B8A0
; File offset $019870, exact byte SHA256 93978daa35273f3db2a69020a68b1a10f4fec14946506ea2ea7fe3cda7435b57
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B860 | $019870 | AC 09 05 | LDY  $0509
$B863 | $019873 | B9 14 06 | LDA  $0614,Y
$B866 | $019876 | C9 10    | CMP  #$10
$B868 | $019878 | 90 02    | BCC  $B86C
$B86A | $01987A | E9 01    | SBC  #$01
$B86C | $01987C | 85 00    | STA  $00
$B86E | $01987E | AC 0A 05 | LDY  $050A
$B871 | $019881 | B9 14 06 | LDA  $0614,Y
$B874 | $019884 | C9 10    | CMP  #$10
$B876 | $019886 | 90 02    | BCC  $B87A
$B878 | $019888 | E9 01    | SBC  #$01
$B87A | $01988A | 38       | SEC
$B87B | $01988B | E5 00    | SBC  $00
$B87D | $01988D | B0 05    | BCS  $B884
$B87F | $01988F | 49 FF    | EOR  #$FF
$B881 | $019891 | 18       | CLC
$B882 | $019892 | 69 01    | ADC  #$01
$B884 | $019894 | 85 00    | STA  $00
$B886 | $019896 | AC 0A 05 | LDY  $050A
$B889 | $019899 | B9 00 06 | LDA  $0600,Y
$B88C | $01989C | 38       | SEC
$B88D | $01989D | AC 09 05 | LDY  $0509
$B890 | $0198A0 | F9 00 06 | SBC  $0600,Y
$B893 | $0198A3 | B0 05    | BCS  $B89A
$B895 | $0198A5 | 49 FF    | EOR  #$FF
$B897 | $0198A7 | 18       | CLC
$B898 | $0198A8 | 69 01    | ADC  #$01
$B89A | $0198AA | C5 00    | CMP  $00
$B89C | $0198AC | B0 02    | BCS  $B8A0
$B89E | $0198AE | A5 00    | LDA  $00
$B8A0 | $0198B0 | 60       | RTS
