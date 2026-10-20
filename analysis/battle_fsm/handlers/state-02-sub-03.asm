; main=2 sub=3: 普通攻击目标选择
; entry bank12 $A325; file $018335
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
018335 b12:$A325 AD 87 00       LDA  $0087
018338 b12:$A328 10 3D          BPL  $A367
01833A b12:$A32A A9 05          LDA  #$05
01833C b12:$A32C 8D 7A 00       STA  $007A
01833F b12:$A32F A9 00          LDA  #$00
018341 b12:$A331 8D 40 05       STA  $0540
018344 b12:$A334 8D 41 05       STA  $0541
018347 b12:$A337 8D 42 05       STA  $0542
01834A b12:$A33A 8D 43 05       STA  $0543
01834D b12:$A33D 8D A4 00       STA  $00A4
018350 b12:$A340 A5 90          LDA  $90
018352 b12:$A342 8D 10 05       STA  $0510
018355 b12:$A345 A5 91          LDA  $91
018357 b12:$A347 8D 11 05       STA  $0511
01835A b12:$A34A A5 8E          LDA  $8E
01835C b12:$A34C 8D 12 05       STA  $0512
01835F b12:$A34F A5 8F          LDA  $8F
018361 b12:$A351 8D 13 05       STA  $0513
018364 b12:$A354 AC 09 05       LDY  $0509
018367 b12:$A357 B9 00 06       LDA  $0600,Y
01836A b12:$A35A 85 10          STA  $10
01836C b12:$A35C B9 14 06       LDA  $0614,Y
01836F b12:$A35F 85 11          STA  $11
018371 b12:$A361 20 46 DB       JSR  $DB46 ; cpu_DB46
018374 b12:$A364 8D 44 05       STA  $0544
018377 b12:$A367 60             RTS
