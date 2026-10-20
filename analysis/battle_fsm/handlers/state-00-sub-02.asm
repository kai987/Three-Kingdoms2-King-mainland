; main=0 sub=2: 单位选择与行动菜单
; entry bank12 $A0BB; file $0180CB
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0180CB b12:$A0BB 20 EE D5       JSR  $D5EE ; battle_cursor_input
0180CE b12:$A0BE 20 57 D6       JSR  $D657 ; draw_battle_cursor
0180D1 b12:$A0C1 20 27 DF       JSR  $DF27 ; text_jobs_idle
0180D4 b12:$A0C4 B0 01          BCS  $A0C7
0180D6 b12:$A0C6 60             RTS
0180D7 b12:$A0C7 20 FB D4       JSR  $D4FB ; direction_repeat_input
0180DA b12:$A0CA A5 81          LDA  $81
0180DC b12:$A0CC 29 01          AND  #$01
0180DE b12:$A0CE F0 2B          BEQ  $A0FB
0180E0 b12:$A0D0 20 8A D6       JSR  $D68A ; find_unit_at_cursor
0180E3 b12:$A0D3 98             TYA
0180E4 b12:$A0D4 30 25          BMI  $A0FB
0180E6 b12:$A0D6 20 4B DC       JSR  $DC4B ; target_side_filter
0180E9 b12:$A0D9 C9 FF          CMP  #$FF
0180EB b12:$A0DB F0 1E          BEQ  $A0FB
0180ED b12:$A0DD 8C 09 05       STY  $0509
0180F0 b12:$A0E0 8C 0A 05       STY  $050A
0180F3 b12:$A0E3 EE 01 05       INC  $0501
0180F6 b12:$A0E6 A0 3D          LDY  #$3D
0180F8 b12:$A0E8 20 07 EE       JSR  $EE07 ; far_A027
; inline .word $A027, resumes $A0ED
0180FD b12:$A0ED A9 C1          LDA  #$C1
0180FF b12:$A0EF 20 83 F2       JSR  $F283 ; queue_message_job_1
018102 b12:$A0F2 A9 00          LDA  #$00
018104 b12:$A0F4 8D 24 04       STA  $0424
018107 b12:$A0F7 8D 25 04       STA  $0425
01810A b12:$A0FA 60             RTS
01810B b12:$A0FB A5 81          LDA  $81
01810D b12:$A0FD 29 02          AND  #$02
01810F b12:$A0FF F0 16          BEQ  $A117
018111 b12:$A101 20 8A D6       JSR  $D68A ; find_unit_at_cursor
018114 b12:$A104 98             TYA
018115 b12:$A105 30 10          BMI  $A117
018117 b12:$A107 8C 09 05       STY  $0509
01811A b12:$A10A 8C 0A 05       STY  $050A
01811D b12:$A10D A9 01          LDA  #$01
01811F b12:$A10F 8D 00 05       STA  $0500
018122 b12:$A112 A9 00          LDA  #$00
018124 b12:$A114 8D 01 05       STA  $0501
018127 b12:$A117 60             RTS
