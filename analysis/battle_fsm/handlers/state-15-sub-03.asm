; main=15 sub=3: 归属结算与返回城市
; entry bank13 $D4F0; file $01B500
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01B500 b13:$D4F0 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01B503 b13:$D4F3 A0 28          LDY  #$28
01B505 b13:$D4F5 20 07 EE       JSR  $EE07 ; far_A006
; inline .word $A006, resumes $D4FA
01B50A b13:$D4FA 60             RTS
