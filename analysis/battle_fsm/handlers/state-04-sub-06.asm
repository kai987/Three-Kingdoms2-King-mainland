; main=4 sub=6: 移动
; entry bank12 $A617; file $018627
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018627 b12:$A617 20 27 DF       JSR  $DF27 ; text_jobs_idle
01862A b12:$A61A 90 23          BCC  $A63F
01862C b12:$A61C 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01862F b12:$A61F A5 81          LDA  $81
018631 b12:$A621 29 03          AND  #$03
018633 b12:$A623 F0 1A          BEQ  $A63F
018635 b12:$A625 AD 2D 04       LDA  $042D
018638 b12:$A628 C9 FF          CMP  #$FF
01863A b12:$A62A D0 14          BNE  $A640
01863C b12:$A62C 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
01863F b12:$A62F A9 1D          LDA  #$1D
018641 b12:$A631 20 73 E6       JSR  $E673 ; fade_or_scene_effect
018644 b12:$A634 A9 00          LDA  #$00
018646 b12:$A636 8D 00 05       STA  $0500
018649 b12:$A639 8D 01 05       STA  $0501
01864C b12:$A63C 20 F7 A1       JSR  $A1F7 ; reset_command_cursor
01864F b12:$A63F 60             RTS
018650 b12:$A640 A9 FF          LDA  #$FF
018652 b12:$A642 8D 2D 04       STA  $042D
018655 b12:$A645 A9 4B          LDA  #$4B
018657 b12:$A647 4C 93 F2       JMP  $F293 ; queue_message_job_0
