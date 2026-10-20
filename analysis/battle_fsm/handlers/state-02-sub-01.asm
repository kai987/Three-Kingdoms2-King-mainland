; main=2 sub=1: 普通攻击目标选择
; entry bank12 $A2BB; file $0182CB
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
0182CB b12:$A2BB AD 0A 05       LDA  $050A
0182CE b12:$A2BE 8D 09 05       STA  $0509
0182D1 b12:$A2C1 20 DE A1       JSR  $A1DE ; blink_menu_cursor
0182D4 b12:$A2C4 20 FB D4       JSR  $D4FB ; direction_repeat_input
0182D7 b12:$A2C7 20 57 D6       JSR  $D657 ; draw_battle_cursor
0182DA b12:$A2CA 20 27 DF       JSR  $DF27 ; text_jobs_idle
0182DD b12:$A2CD 90 3C          BCC  $A30B
0182DF b12:$A2CF A5 81          LDA  $81
0182E1 b12:$A2D1 29 02          AND  #$02
0182E3 b12:$A2D3 F0 0D          BEQ  $A2E2
0182E5 b12:$A2D5 A9 00          LDA  #$00
0182E7 b12:$A2D7 8D 01 05       STA  $0501
0182EA b12:$A2DA A9 00          LDA  #$00
0182EC b12:$A2DC 8D 00 05       STA  $0500
0182EF b12:$A2DF 4C F7 A1       JMP  $A1F7
0182F2 b12:$A2E2 A5 81          LDA  $81
0182F4 b12:$A2E4 29 01          AND  #$01
0182F6 b12:$A2E6 F0 23          BEQ  $A30B
0182F8 b12:$A2E8 20 8A D6       JSR  $D68A ; find_unit_at_cursor
0182FB b12:$A2EB 98             TYA
0182FC b12:$A2EC 30 1D          BMI  $A30B
0182FE b12:$A2EE 20 4B DC       JSR  $DC4B ; target_side_filter
018301 b12:$A2F1 C9 FF          CMP  #$FF
018303 b12:$A2F3 D0 16          BNE  $A30B
018305 b12:$A2F5 8C 09 05       STY  $0509
018308 b12:$A2F8 20 68 A3       JSR  $A368 ; orthogonal_adjacent_target
01830B b12:$A2FB 8A             TXA
01830C b12:$A2FC 30 0D          BMI  $A30B
01830E b12:$A2FE EE 01 05       INC  $0501
018311 b12:$A301 A9 02          LDA  #$02
018313 b12:$A303 8D A4 00       STA  $00A4
018316 b12:$A306 A9 CB          LDA  #$CB
018318 b12:$A308 20 83 F2       JSR  $F283 ; queue_message_job_1
01831B b12:$A30B 60             RTS
