; main=7 sub=0: 待機
; entry bank12 $BCB3; file $019CC3
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019CC3 b12:$BCB3 A9 00          LDA  #$00
019CC5 b12:$BCB5 8D A4 00       STA  $00A4
019CC8 b12:$BCB8 A9 CA          LDA  #$CA
019CCA b12:$BCBA 20 83 F2       JSR  $F283 ; queue_message_job_1
019CCD b12:$BCBD EE 01 05       INC  $0501
019CD0 b12:$BCC0 60             RTS
