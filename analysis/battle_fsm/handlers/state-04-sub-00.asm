; main=4 sub=0: 移动
; entry bank12 $A470; file $018480
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018480 b12:$A470 A9 C6          LDA  #$C6
018482 b12:$A472 20 83 F2       JSR  $F283 ; queue_message_job_1
018485 b12:$A475 EE 01 05       INC  $0501
018488 b12:$A478 A9 00          LDA  #$00
01848A b12:$A47A 8D 0A 05       STA  $050A
01848D b12:$A47D 60             RTS
