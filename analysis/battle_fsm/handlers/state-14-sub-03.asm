; main=14 sub=3: 胜方收容及超额武将转移
; entry bank13 $D3AF; file $01B3BF
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01B3BF b13:$D3AF 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01B3C2 b13:$D3B2 20 27 DF       JSR  $DF27 ; text_jobs_idle
01B3C5 b13:$D3B5 90 1F          BCC  $D3D6
01B3C7 b13:$D3B7 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01B3CA b13:$D3BA A5 81          LDA  $81
01B3CC b13:$D3BC 29 01          AND  #$01
01B3CE b13:$D3BE F0 16          BEQ  $D3D6
01B3D0 b13:$D3C0 A9 00          LDA  #$00
01B3D2 b13:$D3C2 8D 24 04       STA  $0424
01B3D5 b13:$D3C5 8D 25 04       STA  $0425
01B3D8 b13:$D3C8 20 E1 D0       JSR  $D0E1 ; select_next_postbattle_officer
01B3DB b13:$D3CB 8E 0A 05       STX  $050A
01B3DE b13:$D3CE A9 DE          LDA  #$DE
01B3E0 b13:$D3D0 20 8B F2       JSR  $F28B ; queue_message_job_0_variant
01B3E3 b13:$D3D3 EE 01 05       INC  $0501
01B3E6 b13:$D3D6 60             RTS
