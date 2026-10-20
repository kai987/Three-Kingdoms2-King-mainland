; main=11 sub=0: 单挑后升级提示
; entry bank13 $C69F; file $01A6AF
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A6AF b13:$C69F AD 14 05       LDA  $0514
01A6B2 b13:$C6A2 85 10          STA  $10
01A6B4 b13:$C6A4 A9 01          LDA  #$01
01A6B6 b13:$C6A6 8D 70 04       STA  $0470
01A6B9 b13:$C6A9 4C EA C6       JMP  $C6EA
01A6FA b13:$C6EA A0 00          LDY  #$00
01A6FC b13:$C6EC A5 10          LDA  $10
01A6FE b13:$C6EE CD 60 05       CMP  $0560
01A701 b13:$C6F1 F0 02          BEQ  $C6F5
01A703 b13:$C6F3 A0 01          LDY  #$01
01A705 b13:$C6F5 B9 2E 05       LDA  $052E,Y
01A708 b13:$C6F8 85 11          STA  $11
01A70A b13:$C6FA B9 2C 05       LDA  $052C,Y
01A70D b13:$C6FD 85 12          STA  $12
01A70F b13:$C6FF A5 10          LDA  $10
01A711 b13:$C701 8D 2C 04       STA  $042C
01A714 b13:$C704 20 5B C7       JSR  $C75B ; cpu_C75B
01A717 b13:$C707 C0 FF          CPY  #$FF
01A719 b13:$C709 F0 07          BEQ  $C712
01A71B b13:$C70B B9 A1 6F       LDA  $6FA1,Y
01A71E b13:$C70E C9 FF          CMP  #$FF
01A720 b13:$C710 F0 04          BEQ  $C716
01A722 b13:$C712 EE 01 05       INC  $0501
01A725 b13:$C715 60             RTS
01A726 b13:$C716 AD 2C 04       LDA  $042C
01A729 b13:$C719 20 D7 F2       JSR  $F2D7 ; officer_record_pointer
01A72C b13:$C71C A0 0B          LDY  #$0B
01A72E b13:$C71E B1 00          LDA  ($00),Y
01A730 b13:$C720 29 F0          AND  #$F0
01A732 b13:$C722 C5 12          CMP  $12
01A734 b13:$C724 F0 EC          BEQ  $C712
01A736 b13:$C726 A0 01          LDY  #$01
01A738 b13:$C728 B1 00          LDA  ($00),Y
01A73A b13:$C72A 38             SEC
01A73B b13:$C72B E5 11          SBC  $11
01A73D b13:$C72D 8D 2F 04       STA  $042F
01A740 b13:$C730 A9 00          LDA  #$00
01A742 b13:$C732 8D 2D 04       STA  $042D
01A745 b13:$C735 8D 30 04       STA  $0430
01A748 b13:$C738 8D 31 04       STA  $0431
01A74B b13:$C73B A0 28          LDY  #$28
01A74D b13:$C73D 20 07 EE       JSR  $EE07 ; far_A018
; inline .word $A018, resumes $C742
01A752 b13:$C742 A9 03          LDA  #$03
01A754 b13:$C744 8D 01 05       STA  $0501
01A757 b13:$C747 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
01A75A b13:$C74A A9 7B          LDA  #$7B
01A75C b13:$C74C 20 8B E6       JSR  $E68B ; scene_sound_or_effect
01A75F b13:$C74F A9 4A          LDA  #$4A
01A761 b13:$C751 AC 2F 04       LDY  $042F
01A764 b13:$C754 D0 02          BNE  $C758
01A766 b13:$C756 A9 4D          LDA  #$4D
01A768 b13:$C758 4C 93 F2       JMP  $F293 ; queue_message_job_0
