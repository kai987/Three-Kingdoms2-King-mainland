; main=6 sub=2: 退却
; entry bank12 $B9B6; file $0199C6
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018207 b12:$A1F7 A9 05          LDA  #$05
018209 b12:$A1F9 20 93 F2       JSR  $F293 ; queue_message_job_0
01820C b12:$A1FC A9 01          LDA  #$01
01820E b12:$A1FE 85 12          STA  $12
018210 b12:$A200 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
018213 b12:$A203 A9 00          LDA  #$00
018215 b12:$A205 8D 24 04       STA  $0424
018218 b12:$A208 8D 25 04       STA  $0425
01821B b12:$A20B 60             RTS
0199C5 b12:$B9B5 60             RTS
0199C6 b12:$B9B6 20 DE A1       JSR  $A1DE ; blink_menu_cursor
0199C9 b12:$B9B9 AD 0A 05       LDA  $050A
0199CC b12:$B9BC 0A             ASL  A
0199CD b12:$B9BD A8             TAY
0199CE b12:$B9BE B9 9F BA       LDA  $BA9F,Y
0199D1 b12:$B9C1 85 10          STA  $10
0199D3 b12:$B9C3 B9 A0 BA       LDA  $BAA0,Y
0199D6 b12:$B9C6 85 11          STA  $11
0199D8 b12:$B9C8 A9 00          LDA  #$00
0199DA b12:$B9CA 85 12          STA  $12
0199DC b12:$B9CC 20 1E ED       JSR  $ED1E ; cpu_ED1E
0199DF b12:$B9CF A9 6F          LDA  #$6F
0199E1 b12:$B9D1 85 10          STA  $10
0199E3 b12:$B9D3 A9 BB          LDA  #$BB
0199E5 b12:$B9D5 85 11          STA  $11
0199E7 b12:$B9D7 A9 7F          LDA  #$7F
0199E9 b12:$B9D9 85 00          STA  $00
0199EB b12:$B9DB A9 BB          LDA  #$BB
0199ED b12:$B9DD 85 01          STA  $01
0199EF b12:$B9DF A5 12          LDA  $12
0199F1 b12:$B9E1 20 F5 ED       JSR  $EDF5 ; cpu_EDF5
0199F4 b12:$B9E4 20 27 DF       JSR  $DF27 ; text_jobs_idle
0199F7 b12:$B9E7 90 CC          BCC  $B9B5
0199F9 b12:$B9E9 A5 81          LDA  $81
0199FB b12:$B9EB 29 02          AND  #$02
0199FD b12:$B9ED F0 0D          BEQ  $B9FC
0199FF b12:$B9EF A9 00          LDA  #$00
019A01 b12:$B9F1 8D 01 05       STA  $0501
019A04 b12:$B9F4 A9 00          LDA  #$00
019A06 b12:$B9F6 8D 00 05       STA  $0500
019A09 b12:$B9F9 4C F7 A1       JMP  $A1F7
019A0C b12:$B9FC A5 81          LDA  $81
019A0E b12:$B9FE 29 01          AND  #$01
019A10 b12:$BA00 F0 17          BEQ  $BA19
019A12 b12:$BA02 A4 12          LDY  $12
019A14 b12:$BA04 B9 2C 04       LDA  $042C,Y
019A17 b12:$BA07 8D 0B 05       STA  $050B
019A1A b12:$BA0A 20 11 BC       JSR  $BC11 ; cpu_BC11
019A1D b12:$BA0D 90 0B          BCC  $BA1A
019A1F b12:$BA0F A9 01          LDA  #$01
019A21 b12:$BA11 8D 01 05       STA  $0501
019A24 b12:$BA14 A9 DA          LDA  #$DA
019A26 b12:$BA16 20 83 F2       JSR  $F283 ; queue_message_job_1
019A29 b12:$BA19 60             RTS
019A2A b12:$BA1A EE 01 05       INC  $0501
019A2D b12:$BA1D AD 09 05       LDA  $0509
019A30 b12:$BA20 F0 04          BEQ  $BA26
019A32 b12:$BA22 C9 0A          CMP  #$0A
019A34 b12:$BA24 D0 05          BNE  $BA2B
019A36 b12:$BA26 A9 52          LDA  #$52
019A38 b12:$BA28 4C 83 F2       JMP  $F283 ; queue_message_job_1
019A3B b12:$BA2B A9 C8          LDA  #$C8
019A3D b12:$BA2D 4C 83 F2       JMP  $F283 ; queue_message_job_1
