; main=5 sub=7: 计略选择与效果
; entry bank12 $AAA7; file $018AB7
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018AB7 b12:$AAA7 AD 7E 00       LDA  $007E
018ABA b12:$AAAA D0 36          BNE  $AAE2
018ABC b12:$AAAC AD 0B 05       LDA  $050B
018ABF b12:$AAAF 8D 09 05       STA  $0509
018AC2 b12:$AAB2 A9 01          LDA  #$01
018AC4 b12:$AAB4 85 12          STA  $12
018AC6 b12:$AAB6 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
018AC9 b12:$AAB9 EE 0B 05       INC  $050B
018ACC b12:$AABC AD 0B 05       LDA  $050B
018ACF b12:$AABF C9 14          CMP  #$14
018AD1 b12:$AAC1 90 1F          BCC  $AAE2
018AD3 b12:$AAC3 EE 01 05       INC  $0501
018AD6 b12:$AAC6 AD 44 05       LDA  $0544
018AD9 b12:$AAC9 F0 18          BEQ  $AAE3
018ADB b12:$AACB A9 04          LDA  #$04
018ADD b12:$AACD 8D A4 00       STA  $00A4
018AE0 b12:$AAD0 A9 73          LDA  #$73
018AE2 b12:$AAD2 20 83 F2       JSR  $F283 ; queue_message_job_1
018AE5 b12:$AAD5 AD 0A 05       LDA  $050A
018AE8 b12:$AAD8 8D 09 05       STA  $0509
018AEB b12:$AADB A0 3D          LDY  #$3D
018AED b12:$AADD 20 07 EE       JSR  $EE07 ; far_A027
; inline .word $A027, resumes $AAE2
018AF2 b12:$AAE2 60             RTS
018AF3 b12:$AAE3 A9 03          LDA  #$03
018AF5 b12:$AAE5 8D A4 00       STA  $00A4
018AF8 b12:$AAE8 AD 43 05       LDA  $0543
018AFB b12:$AAEB 29 0F          AND  #$0F
018AFD b12:$AAED A8             TAY
018AFE b12:$AAEE C0 01          CPY  #$01
018B00 b12:$AAF0 F0 10          BEQ  $AB02
018B02 b12:$AAF2 C0 09          CPY  #$09
018B04 b12:$AAF4 D0 1B          BNE  $AB11
018B06 b12:$AAF6 AD 2C 04       LDA  $042C
018B09 b12:$AAF9 D0 07          BNE  $AB02
018B0B b12:$AAFB AD 2D 04       LDA  $042D
018B0E b12:$AAFE D0 02          BNE  $AB02
018B10 b12:$AB00 A0 01          LDY  #$01
018B12 b12:$AB02 AD 32 04       LDA  $0432
018B15 b12:$AB05 C9 FF          CMP  #$FF
018B17 b12:$AB07 F0 08          BEQ  $AB11
018B19 b12:$AB09 8D 2C 04       STA  $042C
018B1C b12:$AB0C A9 4E          LDA  #$4E
018B1E b12:$AB0E 4C 93 F2       JMP  $F293 ; queue_message_job_0
018B21 b12:$AB11 B9 1A AB       LDA  $AB1A,Y
018B24 b12:$AB14 20 83 F2       JSR  $F283 ; queue_message_job_1
018B27 b12:$AB17 4C D5 AA       JMP  $AAD5
