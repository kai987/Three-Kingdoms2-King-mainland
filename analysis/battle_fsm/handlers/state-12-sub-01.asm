; main=12 sub=1: 战斗结果确认
; entry bank13 $C9AD; file $01A9BD
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A9BD b13:$C9AD 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A9C0 b13:$C9B0 90 10          BCC  $C9C2
01A9C2 b13:$C9B2 AD 7E 00       LDA  $007E
01A9C5 b13:$C9B5 D0 0B          BNE  $C9C2
01A9C7 b13:$C9B7 EE 01 05       INC  $0501
01A9CA b13:$C9BA 20 53 CA       JSR  $CA53 ; cpu_CA53
01A9CD b13:$C9BD A9 04          LDA  #$04
01A9CF b13:$C9BF 20 8B F2       JSR  $F28B ; queue_message_job_0_variant
01A9D2 b13:$C9C2 60             RTS
