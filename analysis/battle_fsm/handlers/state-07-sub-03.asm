; main=7 sub=3: 待機
; entry bank12 $BD13; file $019D23
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019D23 b12:$BD13 20 27 DF       JSR  $DF27 ; text_jobs_idle
019D26 b12:$BD16 90 13          BCC  $BD2B
019D28 b12:$BD18 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
019D2B b12:$BD1B A5 81          LDA  $81
019D2D b12:$BD1D 29 03          AND  #$03
019D2F b12:$BD1F F0 0A          BEQ  $BD2B
019D31 b12:$BD21 A9 0C          LDA  #$0C
019D33 b12:$BD23 8D 00 05       STA  $0500
019D36 b12:$BD26 A9 00          LDA  #$00
019D38 b12:$BD28 8D 01 05       STA  $0501
019D3B b12:$BD2B 60             RTS
