; main=5 sub=9: 计略选择与效果
; entry bank12 $AB52; file $018B62
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
018B62 b12:$AB52 20 27 DF       JSR  $DF27 ; text_jobs_idle
018B65 b12:$AB55 90 2E          BCC  $AB85
018B67 b12:$AB57 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
018B6A b12:$AB5A A5 81          LDA  $81
018B6C b12:$AB5C 29 01          AND  #$01
018B6E b12:$AB5E F0 25          BEQ  $AB85
018B70 b12:$AB60 AD 2D 04       LDA  $042D
018B73 b12:$AB63 C9 FF          CMP  #$FF
018B75 b12:$AB65 D0 1F          BNE  $AB86
018B77 b12:$AB67 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
018B7A b12:$AB6A A9 1D          LDA  #$1D
018B7C b12:$AB6C 20 73 E6       JSR  $E673 ; fade_or_scene_effect
018B7F b12:$AB6F A0 03          LDY  #$03
018B81 b12:$AB71 B9 6C 04       LDA  $046C,Y
018B84 b12:$AB74 99 3F 6F       STA  $6F3F,Y
018B87 b12:$AB77 88             DEY
018B88 b12:$AB78 10 F7          BPL  $AB71
018B8A b12:$AB7A A9 00          LDA  #$00
018B8C b12:$AB7C 8D 01 05       STA  $0501
018B8F b12:$AB7F 8D 00 05       STA  $0500
018B92 b12:$AB82 4C F7 A1       JMP  $A1F7
018B95 b12:$AB85 60             RTS
018B96 b12:$AB86 A9 FF          LDA  #$FF
018B98 b12:$AB88 8D 2D 04       STA  $042D
018B9B b12:$AB8B A9 4B          LDA  #$4B
018B9D b12:$AB8D 4C 93 F2       JMP  $F293 ; queue_message_job_0
