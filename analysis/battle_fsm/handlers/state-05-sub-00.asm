; main=5 sub=0: 计略选择与效果
; entry bank12 $A89E; file $0188AE
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0188AE b12:$A89E A9 F3          LDA  #$F3
0188B0 b12:$A8A0 8D 10 03       STA  $0310
0188B3 b12:$A8A3 A9 00          LDA  #$00
0188B5 b12:$A8A5 8D 00 03       STA  $0300
0188B8 b12:$A8A8 8D 0B 05       STA  $050B
0188BB b12:$A8AB A0 03          LDY  #$03
0188BD b12:$A8AD B9 3F 6F       LDA  $6F3F,Y
0188C0 b12:$A8B0 99 6C 04       STA  $046C,Y
0188C3 b12:$A8B3 88             DEY
0188C4 b12:$A8B4 10 F7          BPL  $A8AD
0188C6 b12:$A8B6 EE 01 05       INC  $0501
0188C9 b12:$A8B9 A0 28          LDY  #$28
0188CB b12:$A8BB 20 07 EE       JSR  $EE07 ; far_A01B
; inline .word $A01B, resumes $A8C0
0188D0 b12:$A8C0 60             RTS
