;Adds to rawword, masks result to10 bits and caps999; prior amount and later AP excluded.
;Exact bounded entry/prefix; no linear-data-as-code claim.
015FA5 b10:$BF95 A0 08      LDY  #$08
015FA7 b10:$BF97 B1 20      LDA  ($20),Y
015FA9 b10:$BF99 18         CLC
015FAA b10:$BF9A 65 22      ADC  $22
015FAC b10:$BF9C 91 20      STA  ($20),Y
015FAE b10:$BF9E C8         INY
015FAF b10:$BF9F B1 20      LDA  ($20),Y
015FB1 b10:$BFA1 65 23      ADC  $23
015FB3 b10:$BFA3 29 03      AND  #$03
015FB5 b10:$BFA5 91 20      STA  ($20),Y
015FB7 b10:$BFA7 C9 03      CMP  #$03
015FB9 b10:$BFA9 90 10      BCC  $BFBB
015FBB b10:$BFAB 88         DEY
015FBC b10:$BFAC B1 20      LDA  ($20),Y
015FBE b10:$BFAE C9 E7      CMP  #$E7
015FC0 b10:$BFB0 90 09      BCC  $BFBB
015FC2 b10:$BFB2 A9 E7      LDA  #$E7
015FC4 b10:$BFB4 91 20      STA  ($20),Y
015FC6 b10:$BFB6 C8         INY
015FC7 b10:$BFB7 A9 03      LDA  #$03
015FC9 b10:$BFB9 91 20      STA  ($20),Y
