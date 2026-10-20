; main=5 sub=5: 计略选择与效果
; entry bank12 $AA2E; file $018A3E
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018A3E b12:$AA2E 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
018A41 b12:$AA31 20 57 D6       JSR  $D657 ; draw_battle_cursor
018A44 b12:$AA34 20 27 DF       JSR  $DF27 ; text_jobs_idle
018A47 b12:$AA37 90 32          BCC  $AA6B
018A49 b12:$AA39 A5 81          LDA  $81
018A4B b12:$AA3B 29 01          AND  #$01
018A4D b12:$AA3D F0 2C          BEQ  $AA6B
018A4F b12:$AA3F EE 01 05       INC  $0501
018A52 b12:$AA42 A9 89          LDA  #$89
018A54 b12:$AA44 85 C3          STA  $C3
018A56 b12:$AA46 A9 8A          LDA  #$8A
018A58 b12:$AA48 85 C4          STA  $C4
018A5A b12:$AA4A A9 88          LDA  #$88
018A5C b12:$AA4C 85 C5          STA  $C5
018A5E b12:$AA4E 85 C2          STA  $C2
018A60 b12:$AA50 AC 09 05       LDY  $0509
018A63 b12:$AA53 A9 00          LDA  #$00
018A65 b12:$AA55 99 50 06       STA  $0650,Y
018A68 b12:$AA58 AD 43 05       LDA  $0543
018A6B b12:$AA5B 18             CLC
018A6C b12:$AA5C 69 01          ADC  #$01
018A6E b12:$AA5E 8D C8 04       STA  $04C8
018A71 b12:$AA61 A9 05          LDA  #$05
018A73 b12:$AA63 8D 10 03       STA  $0310
018A76 b12:$AA66 A9 00          LDA  #$00
018A78 b12:$AA68 8D 00 03       STA  $0300
018A7B b12:$AA6B 60             RTS
