; main=4 sub=2: 移动
; entry bank12 $A4B5; file $0184C5
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0184C5 b12:$A4B5 AC 09 05       LDY  $0509
0184C8 b12:$A4B8 B9 00 06       LDA  $0600,Y
0184CB b12:$A4BB 85 10          STA  $10
0184CD b12:$A4BD B9 14 06       LDA  $0614,Y
0184D0 b12:$A4C0 85 11          STA  $11
0184D2 b12:$A4C2 AD 04 05       LDA  $0504
0184D5 b12:$A4C5 10 0F          BPL  $A4D6
0184D7 b12:$A4C7 20 46 DB       JSR  $DB46 ; cpu_DB46
0184DA b12:$A4CA C9 05          CMP  #$05
0184DC b12:$A4CC D0 08          BNE  $A4D6
0184DE b12:$A4CE A0 28          LDY  #$28
0184E0 b12:$A4D0 20 07 EE       JSR  $EE07 ; far_A027
; inline .word $A027, resumes $A4D5
0184E5 b12:$A4D5 60             RTS
0184E6 b12:$A4D6 AD 0F 05       LDA  $050F
0184E9 b12:$A4D9 C9 03          CMP  #$03
0184EB b12:$A4DB F0 27          BEQ  $A504
0184ED b12:$A4DD A0 31          LDY  #$31
0184EF b12:$A4DF 20 5F F2       JSR  $F25F ; cpu_F25F
0184F2 b12:$A4E2 AD 0E 05       LDA  $050E
0184F5 b12:$A4E5 0A             ASL  A
0184F6 b12:$A4E6 85 00          STA  $00
0184F8 b12:$A4E8 0A             ASL  A
0184F9 b12:$A4E9 18             CLC
0184FA b12:$A4EA 65 00          ADC  $00
0184FC b12:$A4EC A8             TAY
0184FD b12:$A4ED A2 00          LDX  #$00
0184FF b12:$A4EF B9 A4 9B       LDA  $9BA4,Y
018502 b12:$A4F2 C5 10          CMP  $10
018504 b12:$A4F4 D0 07          BNE  $A4FD
018506 b12:$A4F6 B9 A5 9B       LDA  $9BA5,Y
018509 b12:$A4F9 C5 11          CMP  $11
01850B b12:$A4FB F0 0B          BEQ  $A508
01850D b12:$A4FD C8             INY
01850E b12:$A4FE C8             INY
01850F b12:$A4FF E8             INX
018510 b12:$A500 E0 03          CPX  #$03
018512 b12:$A502 90 EB          BCC  $A4EF
018514 b12:$A504 EE 01 05       INC  $0501
018517 b12:$A507 60             RTS
018518 b12:$A508 8E 70 04       STX  $0470
01851B b12:$A50B A9 01          LDA  #$01
01851D b12:$A50D 85 12          STA  $12
01851F b12:$A50F 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
018522 b12:$A512 A9 09          LDA  #$09
018524 b12:$A514 8D 00 05       STA  $0500
018527 b12:$A517 8D 01 05       STA  $0501
01852A b12:$A51A A9 A7          LDA  #$A7
01852C b12:$A51C 4C 93 F2       JMP  $F293 ; queue_message_job_0
