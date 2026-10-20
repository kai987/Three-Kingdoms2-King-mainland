; main=8 sub=2: 电脑方行动桥接
; entry bank12 $BF01; file $019F11
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019F11 b12:$BF01 AC 8F 6F       LDY  $6F8F
019F14 b12:$BF04 B9 14 BF       LDA  $BF14,Y
019F17 b12:$BF07 8D 01 05       STA  $0501
019F1A b12:$BF0A C9 0C          CMP  #$0C
019F1C b12:$BF0C D0 05          BNE  $BF13
019F1E b12:$BF0E A9 05          LDA  #$05
019F20 b12:$BF10 20 93 F2       JSR  $F293 ; queue_message_job_0
019F23 b12:$BF13 60             RTS
