; main=0 sub=3: 单位选择与行动菜单
; entry bank12 $A118; file $018128
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018127 b12:$A117 60             RTS
018128 b12:$A118 A9 00          LDA  #$00
01812A b12:$A11A 8D A4 00       STA  $00A4
01812D b12:$A11D 20 33 DC       JSR  $DC33 ; draw_active_unit
018130 b12:$A120 20 DE A1       JSR  $A1DE ; blink_menu_cursor
018133 b12:$A123 A9 93          LDA  #$93
018135 b12:$A125 85 10          STA  $10
018137 b12:$A127 A9 A1          LDA  #$A1
018139 b12:$A129 85 11          STA  $11
01813B b12:$A12B A9 00          LDA  #$00
01813D b12:$A12D 85 12          STA  $12
01813F b12:$A12F 20 1E ED       JSR  $ED1E ; cpu_ED1E
018142 b12:$A132 A9 9B          LDA  #$9B
018144 b12:$A134 85 10          STA  $10
018146 b12:$A136 A9 A1          LDA  #$A1
018148 b12:$A138 85 11          STA  $11
01814A b12:$A13A A9 A7          LDA  #$A7
01814C b12:$A13C 85 00          STA  $00
01814E b12:$A13E A9 A1          LDA  #$A1
018150 b12:$A140 85 01          STA  $01
018152 b12:$A142 A5 12          LDA  $12
018154 b12:$A144 20 F5 ED       JSR  $EDF5 ; cpu_EDF5
018157 b12:$A147 20 27 DF       JSR  $DF27 ; text_jobs_idle
01815A b12:$A14A 90 CB          BCC  $A117
01815C b12:$A14C A5 81          LDA  $81
01815E b12:$A14E 29 02          AND  #$02
018160 b12:$A150 F0 08          BEQ  $A15A
018162 b12:$A152 A9 00          LDA  #$00
018164 b12:$A154 8D 01 05       STA  $0501
018167 b12:$A157 4C F7 A1       JMP  $A1F7
01816A b12:$A15A A5 81          LDA  $81
01816C b12:$A15C 29 01          AND  #$01
01816E b12:$A15E F0 32          BEQ  $A192
018170 b12:$A160 A4 12          LDY  $12
018172 b12:$A162 D0 10          BNE  $A174
018174 b12:$A164 AE 09 05       LDX  $0509
018177 b12:$A167 BD 50 06       LDA  $0650,X
01817A b12:$A16A F0 08          BEQ  $A174
01817C b12:$A16C EE 01 05       INC  $0501
01817F b12:$A16F A9 BC          LDA  #$BC
018181 b12:$A171 4C 83 F2       JMP  $F283 ; queue_message_job_1
018184 b12:$A174 C0 01          CPY  #$01
018186 b12:$A176 D0 07          BNE  $A17F
018188 b12:$A178 AD 05 05       LDA  $0505
01818B b12:$A17B C9 02          CMP  #$02
01818D b12:$A17D 90 13          BCC  $A192
01818F b12:$A17F B9 AC A1       LDA  $A1AC,Y
018192 b12:$A182 8D 00 05       STA  $0500
018195 b12:$A185 B9 B2 A1       LDA  $A1B2,Y
018198 b12:$A188 8D 01 05       STA  $0501
01819B b12:$A18B A9 01          LDA  #$01
01819D b12:$A18D 85 12          STA  $12
01819F b12:$A18F 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
0181A2 b12:$A192 60             RTS
018207 b12:$A1F7 A9 05          LDA  #$05
018209 b12:$A1F9 20 93 F2       JSR  $F293 ; queue_message_job_0
01820C b12:$A1FC A9 01          LDA  #$01
01820E b12:$A1FE 85 12          STA  $12
018210 b12:$A200 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
018213 b12:$A203 A9 00          LDA  #$00
018215 b12:$A205 8D 24 04       STA  $0424
018218 b12:$A208 8D 25 04       STA  $0425
01821B b12:$A20B 60             RTS
