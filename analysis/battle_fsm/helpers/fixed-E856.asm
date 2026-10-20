; bank31 $E856, file $03E866
; E87A draw AND7 (0..7)
03E866 b31:$E856 20 7A E8       JSR  $E87A
03E869 b31:$E859 29 07          AND  #$07
03E86B b31:$E85B 60             RTS
