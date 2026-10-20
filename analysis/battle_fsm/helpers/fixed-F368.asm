; bank31 $F368, file $03F378
; Ruler pointer lookup F379[(A&15)*2] -> $00..01; proven ruler domain0..6
03F378 b31:$F368 29 0F          AND  #$0F
03F37A b31:$F36A 0A             ASL  A
03F37B b31:$F36B A8             TAY
03F37C b31:$F36C B9 79 F3       LDA  $F379,Y
03F37F b31:$F36F 8D 00 00       STA  $0000
03F382 b31:$F372 B9 7A F3       LDA  $F37A,Y
03F385 b31:$F375 8D 01 00       STA  $0001
03F388 b31:$F378 60             RTS
