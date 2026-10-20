; main=5 sub=8: 计略选择与效果
; entry bank12 $AB2A; file $018B3A
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
018B3A b12:$AB2A 20 27 DF       JSR  $DF27 ; text_jobs_idle
018B3D b12:$AB2D 90 22          BCC  $AB51
018B3F b12:$AB2F 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
018B42 b12:$AB32 A5 81          LDA  $81
018B44 b12:$AB34 29 01          AND  #$01
018B46 b12:$AB36 F0 19          BEQ  $AB51
018B48 b12:$AB38 AC 0A 05       LDY  $050A
018B4B b12:$AB3B B9 64 06       LDA  $0664,Y
018B4E b12:$AB3E 8D 2C 04       STA  $042C
018B51 b12:$AB41 20 E9 DE       JSR  $DEE9 ; cpu_DEE9
018B54 b12:$AB44 90 29          BCC  $AB6F
018B56 b12:$AB46 EE 01 05       INC  $0501
018B59 b12:$AB49 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
018B5C b12:$AB4C A9 7B          LDA  #$7B
018B5E b12:$AB4E 20 8B E6       JSR  $E68B ; scene_sound_or_effect
018B61 b12:$AB51 60             RTS
018B7F b12:$AB6F A0 03          LDY  #$03
018B81 b12:$AB71 B9 6C 04       LDA  $046C,Y
018B84 b12:$AB74 99 3F 6F       STA  $6F3F,Y
018B87 b12:$AB77 88             DEY
018B88 b12:$AB78 10 F7          BPL  $AB71
018B8A b12:$AB7A A9 00          LDA  #$00
018B8C b12:$AB7C 8D 01 05       STA  $0501
018B8F b12:$AB7F 8D 00 05       STA  $0500
018B92 b12:$AB82 4C F7 A1       JMP  $A1F7
