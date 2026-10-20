; main=5 sub=2: 计略选择与效果
; entry bank12 $A8D8; file $0188E8
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0188E8 b12:$A8D8 A9 C7          LDA  #$C7
0188EA b12:$A8DA 20 83 F2       JSR  $F283 ; queue_message_job_1
0188ED b12:$A8DD EE 01 05       INC  $0501
0188F0 b12:$A8E0 A9 E1          LDA  #$E1
0188F2 b12:$A8E2 85 E7          STA  $E7
0188F4 b12:$A8E4 A9 E1          LDA  #$E1
0188F6 b12:$A8E6 85 E9          STA  $E9
0188F8 b12:$A8E8 A9 02          LDA  #$02
0188FA b12:$A8EA 85 B4          STA  $B4
0188FC b12:$A8EC A9 16          LDA  #$16
0188FE b12:$A8EE 85 B3          STA  $B3
018900 b12:$A8F0 A9 17          LDA  #$17
018902 b12:$A8F2 85 B5          STA  $B5
018904 b12:$A8F4 A9 5B          LDA  #$5B
018906 b12:$A8F6 85 B2          STA  $B2
018908 b12:$A8F8 A5 8E          LDA  $8E
01890A b12:$A8FA 8D 40 05       STA  $0540
01890D b12:$A8FD A5 90          LDA  $90
01890F b12:$A8FF 8D 41 05       STA  $0541
018912 b12:$A902 A9 00          LDA  #$00
018914 b12:$A904 85 8E          STA  $8E
018916 b12:$A906 A9 50          LDA  #$50
018918 b12:$A908 85 90          STA  $90
01891A b12:$A90A A9 01          LDA  #$01
01891C b12:$A90C 85 8F          STA  $8F
01891E b12:$A90E A9 00          LDA  #$00
018920 b12:$A910 8D 24 04       STA  $0424
018923 b12:$A913 8D 25 04       STA  $0425
018926 b12:$A916 60             RTS
