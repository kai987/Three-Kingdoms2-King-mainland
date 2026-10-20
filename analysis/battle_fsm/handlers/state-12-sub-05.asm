; main=12 sub=5: 战斗结果确认
; entry bank13 $CA2F; file $01AA3F
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AA3F b13:$CA2F 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AA42 b13:$CA32 20 27 DF       JSR  $DF27 ; text_jobs_idle
01AA45 b13:$CA35 90 09          BCC  $CA40
01AA47 b13:$CA37 A5 81          LDA  $81
01AA49 b13:$CA39 29 01          AND  #$01
01AA4B b13:$CA3B F0 03          BEQ  $CA40
01AA4D b13:$CA3D CE 01 05       DEC  $0501
01AA50 b13:$CA40 60             RTS
