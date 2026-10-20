; main=6 sub=1: 退却
; entry bank12 $B96D; file $01997D
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
01997D b12:$B96D 20 70 DC       JSR  $DC70 ; dialog_navigation
019980 b12:$B970 20 DE A1       JSR  $A1DE ; blink_menu_cursor
019983 b12:$B973 20 27 DF       JSR  $DF27 ; text_jobs_idle
019986 b12:$B976 90 3D          BCC  $B9B5
019988 b12:$B978 A5 81          LDA  $81
01998A b12:$B97A 29 02          AND  #$02
01998C b12:$B97C F0 0D          BEQ  $B98B
01998E b12:$B97E A9 00          LDA  #$00
019990 b12:$B980 8D 01 05       STA  $0501
019993 b12:$B983 A9 00          LDA  #$00
019995 b12:$B985 8D 00 05       STA  $0500
019998 b12:$B988 4C F7 A1       JMP  $A1F7
01999B b12:$B98B A5 81          LDA  $81
01999D b12:$B98D 29 01          AND  #$01
01999F b12:$B98F F0 24          BEQ  $B9B5
0199A1 b12:$B991 EE 01 05       INC  $0501
0199A4 b12:$B994 A9 D7          LDA  #$D7
0199A6 b12:$B996 20 83 F2       JSR  $F283 ; queue_message_job_1
0199A9 b12:$B999 A9 00          LDA  #$00
0199AB b12:$B99B 8D 24 04       STA  $0424
0199AE b12:$B99E 8D 25 04       STA  $0425
0199B1 b12:$B9A1 20 84 BB       JSR  $BB84 ; cpu_BB84
0199B4 b12:$B9A4 AD 0A 05       LDA  $050A
0199B7 b12:$B9A7 C9 FF          CMP  #$FF
0199B9 b12:$B9A9 D0 0A          BNE  $B9B5
0199BB b12:$B9AB A9 05          LDA  #$05
0199BD b12:$B9AD 8D 01 05       STA  $0501
0199C0 b12:$B9B0 A9 D9          LDA  #$D9
0199C2 b12:$B9B2 20 83 F2       JSR  $F283 ; queue_message_job_1
0199C5 b12:$B9B5 60             RTS
