; main=10 sub=4: 下一方回合准备
; entry bank13 $C2F7; file $01A307
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A307 b13:$C2F7 20 27 DF       JSR  $DF27 ; text_jobs_idle
01A30A b13:$C2FA 90 11          BCC  $C30D
01A30C b13:$C2FC 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01A30F b13:$C2FF A5 81          LDA  $81
01A311 b13:$C301 29 01          AND  #$01
01A313 b13:$C303 F0 08          BEQ  $C30D
01A315 b13:$C305 EE 01 05       INC  $0501
01A318 b13:$C308 A9 FF          LDA  #$FF
01A31A b13:$C30A 8D 0A 05       STA  $050A
01A31D b13:$C30D 60             RTS
