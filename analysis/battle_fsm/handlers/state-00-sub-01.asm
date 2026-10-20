; main=0 sub=1: 单位选择与行动菜单
; entry bank12 $A08D; file $01809D
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01809D b12:$A08D 20 EE D5       JSR  $D5EE ; battle_cursor_input
0180A0 b12:$A090 AD 08 05       LDA  $0508
0180A3 b12:$A093 D0 25          BNE  $A0BA
0180A5 b12:$A095 AD 7E 00       LDA  $007E
0180A8 b12:$A098 D0 20          BNE  $A0BA
0180AA b12:$A09A EE 01 05       INC  $0501
0180AD b12:$A09D A9 C0          LDA  #$C0
0180AF b12:$A09F 20 93 F2       JSR  $F293 ; queue_message_job_0
0180B2 b12:$A0A2 AD 07 05       LDA  $0507
0180B5 b12:$A0A5 AC 04 05       LDY  $0504
0180B8 b12:$A0A8 10 04          BPL  $A0AE
0180BA b12:$A0AA 4A             LSR  A
0180BB b12:$A0AB 4A             LSR  A
0180BC b12:$A0AC 4A             LSR  A
0180BD b12:$A0AD 4A             LSR  A
0180BE b12:$A0AE 29 0F          AND  #$0F
0180C0 b12:$A0B0 20 68 F3       JSR  $F368 ; ruler_record_pointer
0180C3 b12:$A0B3 A0 00          LDY  #$00
0180C5 b12:$A0B5 B1 00          LDA  ($00),Y
0180C7 b12:$A0B7 8D 2C 04       STA  $042C
0180CA b12:$A0BA 60             RTS
