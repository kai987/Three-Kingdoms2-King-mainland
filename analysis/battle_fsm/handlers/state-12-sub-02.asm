; main=12 sub=2: 战斗结果确认
; entry bank13 $C9C3; file $01A9D3
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A9D2 b13:$C9C2 60             RTS
01A9D3 b13:$C9C3 AD 7E 00       LDA  $007E
01A9D6 b13:$C9C6 D0 FA          BNE  $C9C2
01A9D8 b13:$C9C8 A9 E1          LDA  #$E1
01A9DA b13:$C9CA 85 E6          STA  $E6
01A9DC b13:$C9CC A9 E1          LDA  #$E1
01A9DE b13:$C9CE 85 E8          STA  $E8
01A9E0 b13:$C9D0 A9 08          LDA  #$08
01A9E2 b13:$C9D2 85 B2          STA  $B2
01A9E4 b13:$C9D4 A9 09          LDA  #$09
01A9E6 b13:$C9D6 85 B3          STA  $B3
01A9E8 b13:$C9D8 A9 02          LDA  #$02
01A9EA b13:$C9DA 85 B4          STA  $B4
01A9EC b13:$C9DC A9 03          LDA  #$03
01A9EE b13:$C9DE 85 B5          STA  $B5
01A9F0 b13:$C9E0 A9 00          LDA  #$00
01A9F2 b13:$C9E2 A2 1F          LDX  #$1F
01A9F4 b13:$C9E4 9D 4C 04       STA  $044C,X
01A9F7 b13:$C9E7 CA             DEX
01A9F8 b13:$C9E8 10 FA          BPL  $C9E4
01A9FA b13:$C9EA A9 00          LDA  #$00
01A9FC b13:$C9EC 85 8E          STA  $8E
01A9FE b13:$C9EE A9 50          LDA  #$50
01AA00 b13:$C9F0 85 90          STA  $90
01AA02 b13:$C9F2 EE 01 05       INC  $0501
01AA05 b13:$C9F5 20 41 CA       JSR  $CA41 ; cpu_CA41
01AA08 b13:$C9F8 A9 18          LDA  #$18
01AA0A b13:$C9FA 20 83 E6       JSR  $E683 ; cpu_E683
01AA0D b13:$C9FD 60             RTS
