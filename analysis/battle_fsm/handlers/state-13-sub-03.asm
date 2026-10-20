; main=13 sub=3: 败方武将转移或转为在野
; entry bank13 $CE56; file $01AE66
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AE66 b13:$CE56 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AE69 b13:$CE59 20 27 DF       JSR  $DF27 ; text_jobs_idle
01AE6C b13:$CE5C 90 17          BCC  $CE75
01AE6E b13:$CE5E 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01AE71 b13:$CE61 A5 81          LDA  $81
01AE73 b13:$CE63 29 01          AND  #$01
01AE75 b13:$CE65 F0 0E          BEQ  $CE75
01AE77 b13:$CE67 20 E1 D0       JSR  $D0E1 ; select_next_postbattle_officer
01AE7A b13:$CE6A 8E 0A 05       STX  $050A
01AE7D b13:$CE6D A9 DE          LDA  #$DE
01AE7F b13:$CE6F 20 8B F2       JSR  $F28B ; queue_message_job_0_variant
01AE82 b13:$CE72 EE 01 05       INC  $0501
01AE85 b13:$CE75 60             RTS
