; bank31 $E850, file $03E860
; E87A draw AND3 (0..3)
03E860 b31:$E850 20 7A E8       JSR  $E87A
03E863 b31:$E853 29 03          AND  #$03
03E865 b31:$E855 60             RTS
