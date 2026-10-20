; main=8 sub=10: 电脑方行动桥接
; entry bank13 $C07D; file $01A08D
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A08D b13:$C07D AC 8E 6F       LDY  $6F8E
01A090 b13:$C080 20 36 DC       JSR  $DC36 ; draw_officer_by_slot
01A093 b13:$C083 AD 8D 6F       LDA  $6F8D
01A096 b13:$C086 8D 43 05       STA  $0543
01A099 b13:$C089 AD 8C 6F       LDA  $6F8C
01A09C b13:$C08C 8D 0A 05       STA  $050A
01A09F b13:$C08F AD 8E 6F       LDA  $6F8E
01A0A2 b13:$C092 8D 09 05       STA  $0509
01A0A5 b13:$C095 AC 09 05       LDY  $0509
01A0A8 b13:$C098 A9 00          LDA  #$00
01A0AA b13:$C09A 99 50 06       STA  $0650,Y
01A0AD b13:$C09D 20 2B B0       JSR  $B02B ; apply_selected_tactic
01A0B0 b13:$C0A0 20 03 DB       JSR  $DB03 ; cpu_DB03
01A0B3 b13:$C0A3 A9 01          LDA  #$01
01A0B5 b13:$C0A5 85 12          STA  $12
01A0B7 b13:$C0A7 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
01A0BA b13:$C0AA A9 0B          LDA  #$0B
01A0BC b13:$C0AC 8D 01 05       STA  $0501
01A0BF b13:$C0AF AD 44 05       LDA  $0544
01A0C2 b13:$C0B2 F0 0A          BEQ  $C0BE
01A0C4 b13:$C0B4 A9 03          LDA  #$03
01A0C6 b13:$C0B6 8D A4 00       STA  $00A4
01A0C9 b13:$C0B9 A9 A2          LDA  #$A2
01A0CB b13:$C0BB 4C 83 F2       JMP  $F283 ; queue_message_job_1
01A0CE b13:$C0BE A9 04          LDA  #$04
01A0D0 b13:$C0C0 8D A4 00       STA  $00A4
01A0D3 b13:$C0C3 AD 43 05       LDA  $0543
01A0D6 b13:$C0C6 29 0F          AND  #$0F
01A0D8 b13:$C0C8 A8             TAY
01A0D9 b13:$C0C9 C0 08          CPY  #$08
01A0DB b13:$C0CB F0 2E          BEQ  $C0FB
01A0DD b13:$C0CD C0 01          CPY  #$01
01A0DF b13:$C0CF F0 10          BEQ  $C0E1
01A0E1 b13:$C0D1 C0 09          CPY  #$09
01A0E3 b13:$C0D3 D0 20          BNE  $C0F5
01A0E5 b13:$C0D5 AD 2C 04       LDA  $042C
01A0E8 b13:$C0D8 D0 07          BNE  $C0E1
01A0EA b13:$C0DA AD 2D 04       LDA  $042D
01A0ED b13:$C0DD D0 02          BNE  $C0E1
01A0EF b13:$C0DF A0 01          LDY  #$01
01A0F1 b13:$C0E1 AD 32 04       LDA  $0432
01A0F4 b13:$C0E4 C9 FF          CMP  #$FF
01A0F6 b13:$C0E6 F0 0D          BEQ  $C0F5
01A0F8 b13:$C0E8 8D 2C 04       STA  $042C
01A0FB b13:$C0EB A9 0F          LDA  #$0F
01A0FD b13:$C0ED 8D 01 05       STA  $0501
01A100 b13:$C0F0 A9 4E          LDA  #$4E
01A102 b13:$C0F2 4C 93 F2       JMP  $F293 ; queue_message_job_0
01A105 b13:$C0F5 B9 00 C1       LDA  $C100,Y
01A108 b13:$C0F8 4C 83 F2       JMP  $F283 ; queue_message_job_1
01A10B b13:$C0FB A9 B7          LDA  #$B7
01A10D b13:$C0FD 4C 93 F2       JMP  $F293 ; queue_message_job_0
