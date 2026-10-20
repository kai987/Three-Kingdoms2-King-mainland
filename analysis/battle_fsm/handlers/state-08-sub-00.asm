; main=8 sub=0: 电脑方行动桥接
; entry bank12 $BEA6; file $019EB6
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019EB6 b12:$BEA6 AD 87 00       LDA  $0087
019EB9 b12:$BEA9 10 0E          BPL  $BEB9
019EBB b12:$BEAB A9 00          LDA  #$00
019EBD b12:$BEAD 8D 8B 6F       STA  $6F8B
019EC0 b12:$BEB0 8D 8D 6F       STA  $6F8D
019EC3 b12:$BEB3 8D 8E 6F       STA  $6F8E
019EC6 b12:$BEB6 EE 01 05       INC  $0501
019EC9 b12:$BEB9 60             RTS
