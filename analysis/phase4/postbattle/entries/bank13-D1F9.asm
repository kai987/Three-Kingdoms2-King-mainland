; apply_selected_officers: City/option30 writeback, status/location and first reference removal
; Source semantics are direct Python; this is exact ROM provenance.
01B209 b13:$D1F9 A0 00          LDY  #$00
01B20B b13:$D1FB B9 80 05       LDA  $0580,Y
01B20E b13:$D1FE 30 07          BMI  $D207
01B210 b13:$D200 98             TYA
01B211 b13:$D201 48             PHA
01B212 b13:$D202 20 0D D2       JSR  $D20D
01B215 b13:$D205 68             PLA
01B216 b13:$D206 A8             TAY
01B217 b13:$D207 C8             INY
01B218 b13:$D208 C0 14          CPY  #$14
01B21A b13:$D20A 90 EF          BCC  $D1FB
01B21C b13:$D20C 60             RTS
