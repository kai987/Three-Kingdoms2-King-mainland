; main=11 sub=3: 单挑后升级提示
; entry bank13 $C6BC; file $01A6CC
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A6CC b13:$C6BC 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A6CF b13:$C6BF 90 1E          BCC  $C6DF
01A6D1 b13:$C6C1 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01A6D4 b13:$C6C4 A5 81          LDA  $81
01A6D6 b13:$C6C6 29 01          AND  #$01
01A6D8 b13:$C6C8 F0 15          BEQ  $C6DF
01A6DA b13:$C6CA AD 2D 04       LDA  $042D
01A6DD b13:$C6CD C9 FF          CMP  #$FF
01A6DF b13:$C6CF D0 0F          BNE  $C6E0
01A6E1 b13:$C6D1 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
01A6E4 b13:$C6D4 A9 1D          LDA  #$1D
01A6E6 b13:$C6D6 20 73 E6       JSR  $E673 ; fade_or_scene_effect
01A6E9 b13:$C6D9 AD 70 04       LDA  $0470
01A6EC b13:$C6DC 8D 01 05       STA  $0501
01A6EF b13:$C6DF 60             RTS
01A6F0 b13:$C6E0 A9 FF          LDA  #$FF
01A6F2 b13:$C6E2 8D 2D 04       STA  $042D
01A6F5 b13:$C6E5 A9 4B          LDA  #$4B
01A6F7 b13:$C6E7 4C 93 F2       JMP  $F293 ; queue_message_job_0
