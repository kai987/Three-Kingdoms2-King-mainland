; main=4 sub=5: 移动
; entry bank12 $A5CE; file $0185DE
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
0185DE b12:$A5CE A9 03          LDA  #$03
0185E0 b12:$A5D0 8D A4 00       STA  $00A4
0185E3 b12:$A5D3 AC 0A 05       LDY  $050A
0185E6 b12:$A5D6 20 36 DC       JSR  $DC36 ; draw_officer_by_slot
0185E9 b12:$A5D9 20 DE A1       JSR  $A1DE ; blink_menu_cursor
0185EC b12:$A5DC 20 27 DF       JSR  $DF27 ; text_jobs_idle
0185EF b12:$A5DF 90 35          BCC  $A616
0185F1 b12:$A5E1 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
0185F4 b12:$A5E4 A5 81          LDA  $81
0185F6 b12:$A5E6 29 03          AND  #$03
0185F8 b12:$A5E8 F0 2C          BEQ  $A616
0185FA b12:$A5EA A0 04          LDY  #$04
0185FC b12:$A5EC AD 04 05       LDA  $0504
0185FF b12:$A5EF 10 02          BPL  $A5F3
018601 b12:$A5F1 A0 00          LDY  #$00
018603 b12:$A5F3 A9 FF          LDA  #$FF
018605 b12:$A5F5 99 D8 04       STA  $04D8,Y
018608 b12:$A5F8 AD 2E 05       LDA  $052E
01860B b12:$A5FB F0 37          BEQ  $A634
01860D b12:$A5FD AC 0A 05       LDY  $050A
018610 b12:$A600 B9 64 06       LDA  $0664,Y
018613 b12:$A603 8D 2C 04       STA  $042C
018616 b12:$A606 20 E9 DE       JSR  $DEE9 ; cpu_DEE9
018619 b12:$A609 90 29          BCC  $A634
01861B b12:$A60B EE 01 05       INC  $0501
01861E b12:$A60E 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
018621 b12:$A611 A9 7B          LDA  #$7B
018623 b12:$A613 20 8B E6       JSR  $E68B ; scene_sound_or_effect
018626 b12:$A616 60             RTS
018644 b12:$A634 A9 00          LDA  #$00
018646 b12:$A636 8D 00 05       STA  $0500
018649 b12:$A639 8D 01 05       STA  $0501
01864C b12:$A63C 20 F7 A1       JSR  $A1F7 ; reset_command_cursor
01864F b12:$A63F 60             RTS
