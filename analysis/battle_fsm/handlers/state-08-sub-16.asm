; main=8 sub=16: 电脑方行动桥接
; entry bank13 $C1EB; file $01A1FB
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A1FB b13:$C1EB 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A1FE b13:$C1EE 90 0B          BCC  $C1FB
01A200 b13:$C1F0 A9 00          LDA  #$00
01A202 b13:$C1F2 8D 00 05       STA  $0500
01A205 b13:$C1F5 8D 01 05       STA  $0501
01A208 b13:$C1F8 8D A4 00       STA  $00A4
01A20B b13:$C1FB 60             RTS
