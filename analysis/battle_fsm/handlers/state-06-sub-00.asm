; main=6 sub=0: 退却
; entry bank12 $B964; file $019974
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019974 b12:$B964 A9 D6          LDA  #$D6
019976 b12:$B966 20 83 F2       JSR  $F283 ; queue_message_job_1
019979 b12:$B969 EE 01 05       INC  $0501
01997C b12:$B96C 60             RTS
