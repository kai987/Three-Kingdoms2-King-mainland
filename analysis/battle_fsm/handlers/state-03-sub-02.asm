; main=3 sub=2: 普通攻击确认
; entry bank12 $A30C; file $01831C
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01831C b12:$A30C 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01831F b12:$A30F A5 81          LDA  $81
018321 b12:$A311 29 01          AND  #$01
018323 b12:$A313 F0 0F          BEQ  $A324
018325 b12:$A315 20 EE EC       JSR  $ECEE ; wait_or_job_barrier
018328 b12:$A318 EE 01 05       INC  $0501
01832B b12:$A31B CE 05 05       DEC  $0505
01832E b12:$A31E CE 05 05       DEC  $0505
018331 b12:$A321 20 D2 A3       JSR  $A3D2 ; prepare_attack_scene_parameters
018334 b12:$A324 60             RTS
