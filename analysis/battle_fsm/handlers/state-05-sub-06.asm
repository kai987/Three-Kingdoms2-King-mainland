; main=5 sub=6: 计略选择与效果
; entry bank12 $AA6C; file $018A7C
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018A7C b12:$AA6C AD C8 04       LDA  $04C8
018A7F b12:$AA6F D0 35          BNE  $AAA6
018A81 b12:$AA71 AC 0A 05       LDY  $050A
018A84 b12:$AA74 B9 64 06       LDA  $0664,Y
018A87 b12:$AA77 20 D7 F2       JSR  $F2D7 ; officer_record_pointer
018A8A b12:$AA7A A0 0B          LDY  #$0B
018A8C b12:$AA7C B1 00          LDA  ($00),Y
018A8E b12:$AA7E 29 F0          AND  #$F0
018A90 b12:$AA80 8D 2C 05       STA  $052C
018A93 b12:$AA83 A0 01          LDY  #$01
018A95 b12:$AA85 B1 00          LDA  ($00),Y
018A97 b12:$AA87 8D 2E 05       STA  $052E
018A9A b12:$AA8A AC 43 05       LDY  $0543
018A9D b12:$AA8D B9 C9 AB       LDA  $ABC9,Y
018AA0 b12:$AA90 85 00          STA  $00
018AA2 b12:$AA92 AD 05 05       LDA  $0505
018AA5 b12:$AA95 38             SEC
018AA6 b12:$AA96 E5 00          SBC  $00
018AA8 b12:$AA98 8D 05 05       STA  $0505
018AAB b12:$AA9B 20 2B B0       JSR  $B02B ; apply_selected_tactic
018AAE b12:$AA9E 20 03 DB       JSR  $DB03 ; cpu_DB03
018AB1 b12:$AAA1 A9 00          LDA  #$00
018AB3 b12:$AAA3 8D 0B 05       STA  $050B
018AB6 b12:$AAA6 60             RTS
