; main=12 sub=0: 战斗结果确认
; entry bank13 $C99E; file $01A9AE
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A9AE b13:$C99E 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
01A9B1 b13:$C9A1 A9 D5          LDA  #$D5
01A9B3 b13:$C9A3 20 93 F2       JSR  $F293 ; queue_message_job_0
01A9B6 b13:$C9A6 20 F8 CA       JSR  $CAF8 ; prepare_postbattle_summary
01A9B9 b13:$C9A9 EE 01 05       INC  $0501
01A9BC b13:$C9AC 60             RTS
