; main=9 sub=0: 村落服务跨银行入口
; entry bank13 $C1FC; file $01A20C
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A20C b13:$C1FC A0 28          LDY  #$28
01A20E b13:$C1FE 20 07 EE       JSR  $EE07 ; far_A009
; inline .word $A009, resumes $C203
01A213 b13:$C203 60             RTS
