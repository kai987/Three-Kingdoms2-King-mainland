; main=5 sub=4: 计略选择与效果
; entry bank12 $A9DD; file $0189ED
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0189ED b12:$A9DD 20 FB D4       JSR  $D4FB ; direction_repeat_input
0189F0 b12:$A9E0 20 EE D5       JSR  $D5EE ; battle_cursor_input
0189F3 b12:$A9E3 20 57 D6       JSR  $D657 ; draw_battle_cursor
0189F6 b12:$A9E6 20 27 DF       JSR  $DF27 ; text_jobs_idle
0189F9 b12:$A9E9 90 3D          BCC  $AA28
0189FB b12:$A9EB A5 81          LDA  $81
0189FD b12:$A9ED 4A             LSR  A
0189FE b12:$A9EE B0 06          BCS  $A9F6
018A00 b12:$A9F0 4A             LSR  A
018A01 b12:$A9F1 B0 30          BCS  $AA23
018A03 b12:$A9F3 4C 28 AA       JMP  $AA28
018A06 b12:$A9F6 20 8A D6       JSR  $D68A ; find_unit_at_cursor
018A09 b12:$A9F9 98             TYA
018A0A b12:$A9FA 30 2C          BMI  $AA28
018A0C b12:$A9FC 20 4B DC       JSR  $DC4B ; target_side_filter
018A0F b12:$A9FF C9 FF          CMP  #$FF
018A11 b12:$AA01 D0 25          BNE  $AA28
018A13 b12:$AA03 8C 09 05       STY  $0509
018A16 b12:$AA06 20 60 B8       JSR  $B860 ; cpu_B860
018A19 b12:$AA09 C9 06          CMP  #$06
018A1B b12:$AA0B B0 1C          BCS  $AA29
018A1D b12:$AA0D 20 80 AD       JSR  $AD80 ; cpu_AD80
018A20 b12:$AA10 B0 0B          BCS  $AA1D
018A22 b12:$AA12 A9 0A          LDA  #$0A
018A24 b12:$AA14 8D 01 05       STA  $0501
018A27 b12:$AA17 A9 F7          LDA  #$F7
018A29 b12:$AA19 20 83 F2       JSR  $F283 ; queue_message_job_1
018A2C b12:$AA1C 60             RTS
018A2D b12:$AA1D EE 01 05       INC  $0501
018A30 b12:$AA20 4C 63 AD       JMP  $AD63
018A33 b12:$AA23 A9 00          LDA  #$00
018A35 b12:$AA25 8D 01 05       STA  $0501
018A38 b12:$AA28 60             RTS
018A39 b12:$AA29 A9 4C          LDA  #$4C
018A3B b12:$AA2B 4C 83 F2       JMP  $F283 ; queue_message_job_1
018D73 b12:$AD63 AD 43 05       LDA  $0543
018D76 b12:$AD66 29 0F          AND  #$0F
018D78 b12:$AD68 A8             TAY
018D79 b12:$AD69 B9 70 AD       LDA  $AD70,Y
018D7C b12:$AD6C 20 83 F2       JSR  $F283 ; queue_message_job_1
018D7F b12:$AD6F 60             RTS
