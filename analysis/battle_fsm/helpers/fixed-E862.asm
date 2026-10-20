; bank31 $E862, file $03E872
; Rejection sample below incoming A; bound<15 masks draw to low4 bits; bound0 never terminates
03E872 b31:$E862 85 10          STA  $10
03E874 b31:$E864 C9 0F          CMP  #$0F
03E876 b31:$E866 B0 0A          BCS  $E872
03E878 b31:$E868 20 7A E8       JSR  $E87A
03E87B b31:$E86B 29 0F          AND  #$0F
03E87D b31:$E86D C5 10          CMP  $10
03E87F b31:$E86F B0 F7          BCS  $E868
03E881 b31:$E871 60             RTS
03E882 b31:$E872 20 7A E8       JSR  $E87A
03E885 b31:$E875 C5 10          CMP  $10
03E887 b31:$E877 B0 F9          BCS  $E872
03E889 b31:$E879 60             RTS
