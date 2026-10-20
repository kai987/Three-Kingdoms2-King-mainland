; main=14 sub=4: 胜方收容及超额武将转移
; entry bank13 $D3D7; file $01B3E7
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01B3E7 b13:$D3D7 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01B3EA b13:$D3DA 20 27 DF       JSR  $DF27 ; text_jobs_idle
01B3ED b13:$D3DD 90 17          BCC  $D3F6
01B3EF b13:$D3DF AE 0A 05       LDX  $050A
01B3F2 b13:$D3E2 A9 FF          LDA  #$FF
01B3F4 b13:$D3E4 9D 2C 04       STA  $042C,X
01B3F7 b13:$D3E7 A9 E0          LDA  #$E0
01B3F9 b13:$D3E9 85 E6          STA  $E6
01B3FB b13:$D3EB 85 E7          STA  $E7
01B3FD b13:$D3ED EE 01 05       INC  $0501
01B400 b13:$D3F0 A9 00          LDA  #$00
01B402 b13:$D3F2 85 8E          STA  $8E
01B404 b13:$D3F4 85 90          STA  $90
01B406 b13:$D3F6 60             RTS
