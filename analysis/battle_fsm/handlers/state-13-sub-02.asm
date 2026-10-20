; main=13 sub=2: 败方武将转移或转为在野
; entry bank13 $CDF2; file $01AE02
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AE02 b13:$CDF2 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AE05 b13:$CDF5 AD 0A 05       LDA  $050A
01AE08 b13:$CDF8 0A             ASL  A
01AE09 b13:$CDF9 A8             TAY
01AE0A b13:$CDFA B9 9F BA       LDA  $BA9F,Y
01AE0D b13:$CDFD 85 10          STA  $10
01AE0F b13:$CDFF B9 A0 BA       LDA  $BAA0,Y
01AE12 b13:$CE02 85 11          STA  $11
01AE14 b13:$CE04 A9 00          LDA  #$00
01AE16 b13:$CE06 85 12          STA  $12
01AE18 b13:$CE08 20 1E ED       JSR  $ED1E ; cpu_ED1E
01AE1B b13:$CE0B A9 6F          LDA  #$6F
01AE1D b13:$CE0D 85 10          STA  $10
01AE1F b13:$CE0F A9 BB          LDA  #$BB
01AE21 b13:$CE11 85 11          STA  $11
01AE23 b13:$CE13 A9 7F          LDA  #$7F
01AE25 b13:$CE15 85 00          STA  $00
01AE27 b13:$CE17 A9 BB          LDA  #$BB
01AE29 b13:$CE19 85 01          STA  $01
01AE2B b13:$CE1B A5 12          LDA  $12
01AE2D b13:$CE1D 20 F5 ED       JSR  $EDF5 ; cpu_EDF5
01AE30 b13:$CE20 20 27 DF       JSR  $DF27 ; text_jobs_idle
01AE33 b13:$CE23 90 30          BCC  $CE55
01AE35 b13:$CE25 A5 81          LDA  $81
01AE37 b13:$CE27 29 01          AND  #$01
01AE39 b13:$CE29 F0 2A          BEQ  $CE55
01AE3B b13:$CE2B A4 12          LDY  $12
01AE3D b13:$CE2D B9 2C 04       LDA  $042C,Y
01AE40 b13:$CE30 8D 40 05       STA  $0540
01AE43 b13:$CE33 8C 41 05       STY  $0541
01AE46 b13:$CE36 C9 1E          CMP  #$1E
01AE48 b13:$CE38 F0 07          BEQ  $CE41
01AE4A b13:$CE3A B9 50 05       LDA  $0550,Y
01AE4D b13:$CE3D C9 0A          CMP  #$0A
01AE4F b13:$CE3F B0 14          BCS  $CE55
01AE51 b13:$CE41 EE 01 05       INC  $0501
01AE54 b13:$CE44 A9 DD          LDA  #$DD
01AE56 b13:$CE46 AC 40 05       LDY  $0540
01AE59 b13:$CE49 C0 1E          CPY  #$1E
01AE5B b13:$CE4B D0 02          BNE  $CE4F
01AE5D b13:$CE4D A9 E5          LDA  #$E5
01AE5F b13:$CE4F 20 83 F2       JSR  $F283 ; queue_message_job_1
01AE62 b13:$CE52 20 C3 D0       JSR  $D0C3 ; cpu_D0C3
01AE65 b13:$CE55 60             RTS
