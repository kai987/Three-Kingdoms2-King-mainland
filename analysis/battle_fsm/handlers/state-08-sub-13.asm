; main=8 sub=13: 电脑方行动桥接
; entry bank13 $C149; file $01A159
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A159 b13:$C149 A0 00          LDY  #$00
01A15B b13:$C14B AD 04 05       LDA  $0504
01A15E b13:$C14E 30 02          BMI  $C152
01A160 b13:$C150 A0 0A          LDY  #$0A
01A162 b13:$C152 98             TYA
01A163 b13:$C153 8D 09 05       STA  $0509
01A166 b13:$C156 A0 3D          LDY  #$3D
01A168 b13:$C158 20 07 EE       JSR  $EE07 ; far_A027
; inline .word $A027, resumes $C15D
01A16D b13:$C15D AD 09 05       LDA  $0509
01A170 b13:$C160 8D 0A 05       STA  $050A
01A173 b13:$C163 AD 8C 6F       LDA  $6F8C
01A176 b13:$C166 8D 09 05       STA  $0509
01A179 b13:$C169 A8             TAY
01A17A b13:$C16A B9 64 06       LDA  $0664,Y
01A17D b13:$C16D 8D 2C 04       STA  $042C
01A180 b13:$C170 EE 01 05       INC  $0501
01A183 b13:$C173 A9 BD          LDA  #$BD
01A185 b13:$C175 4C 83 F2       JMP  $F283 ; queue_message_job_1
