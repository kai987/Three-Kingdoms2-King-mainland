; main=7 sub=2: 待機
; entry bank12 $BCF6; file $019D06
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019D06 b12:$BCF6 A0 3D          LDY  #$3D
019D08 b12:$BCF8 20 07 EE       JSR  $EE07 ; far_A027
; inline .word $A027, resumes $BCFD
019D0D b12:$BCFD AD 2C 04       LDA  $042C
019D10 b12:$BD00 20 68 F3       JSR  $F368 ; ruler_record_pointer
019D13 b12:$BD03 A0 00          LDY  #$00
019D15 b12:$BD05 B1 00          LDA  ($00),Y
019D17 b12:$BD07 8D 2C 04       STA  $042C
019D1A b12:$BD0A EE 01 05       INC  $0501
019D1D b12:$BD0D AD 0A 05       LDA  $050A
019D20 b12:$BD10 4C 83 F2       JMP  $F283 ; queue_message_job_1
