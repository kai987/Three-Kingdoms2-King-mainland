; main=12 sub=3: 战斗结果确认
; entry bank13 $C9FE; file $01AA0E
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AA0E b13:$C9FE 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AA11 b13:$CA01 20 27 DF       JSR  $DF27 ; text_jobs_idle
01AA14 b13:$CA04 90 0C          BCC  $CA12
01AA16 b13:$CA06 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01AA19 b13:$CA09 A5 81          LDA  $81
01AA1B b13:$CA0B 29 01          AND  #$01
01AA1D b13:$CA0D F0 03          BEQ  $CA12
01AA1F b13:$CA0F EE 01 05       INC  $0501
01AA22 b13:$CA12 60             RTS
