
void FUN_bec7(void)

{
  byte bVar1;
  char cVar2;
  char cVar3;
  bool bVar4;
  byte bStack0000;
  
code_r0xbec7:
  do {
    while( true ) {
      bStack0000 = 0xbe;
      FUN_bee6();
      bStack0000 = 0xbe;
      bStack0000 = FUN_d4bb(0x50);
      if ((byte)(&DAT_bedf)[DAT_6f03 & 7] <= bStack0000) {
        FUN_c1e0();
        return;
      }
      bStack0000 = 0xbf;
      bVar1 = FUN_d4bb(100);
      if (bVar1 < 0x28) break;
      cVar2 = 0x45 < bVar1;
      if ((bool)cVar2) {
        cVar2 = 0x59 < bVar1;
        if ((bool)cVar2) {
          DAT_0022._0_1_ = 0x1e;
          DAT_0022._1_1_ = 0;
          DAT_0024 = 0x1e;
          bStack0000 = 0xc1;
          FUN_d36f(DAT_6f5e);
          if (cVar2 != '\0') {
            DAT_002a = (byte)DAT_0022;
            DAT_002b = DAT_0022._1_1_;
            DAT_0022._0_1_ = 0x1e;
            DAT_0022._1_1_ = 0;
            DAT_0024 = 0x1e;
            bStack0000 = 0xc1;
            FUN_d3a9(DAT_6f5e);
            if (cVar2 != '\0') {
              bVar4 = CARRY1((byte)DAT_0022,DAT_002a);
              DAT_002a = (byte)DAT_0022 + DAT_002a;
              DAT_0022._0_1_ = DAT_0022._1_1_ + DAT_002b + bVar4;
              DAT_0020 = CONCAT11(DAT_002a,(undefined1)DAT_0020);
              DAT_0022._1_1_ = (&DAT_c048)[DAT_6f02];
              DAT_0024 = 0;
              bStack0000 = 0xc1;
              DAT_002b = (byte)DAT_0022;
              FUN_d40f();
              DAT_0022._1_1_ = DAT_0020._1_1_;
              bStack0000 = 0xc1;
              FUN_d105(DAT_6f5e);
              bVar1 = *(char *)(DAT_0020 + 0xb) + DAT_0022._1_1_;
              *(byte *)(DAT_0020 + 0xb) = bVar1;
              if (0x62 < bVar1) {
                *(undefined1 *)(DAT_0020 + 0xb) = 99;
              }
              bStack0000 = 0xc1;
              FUN_d152(5);
            }
          }
        }
        else {
          DAT_0022._0_1_ = 10;
          DAT_0022._1_1_ = 0;
          DAT_0024 = 10;
          bStack0000 = 0xc0;
          FUN_d36f(DAT_6f5e);
          if (cVar2 != '\0') {
            DAT_0020 = CONCAT11(DAT_0022._1_1_,(byte)DAT_0022);
            DAT_0022._0_1_ = 0;
            DAT_0022._1_1_ = (&DAT_c045)[DAT_6f02];
            bStack0000 = 0xc0;
            FUN_d438();
            DAT_0020 = CONCAT11(DAT_0026,(undefined1)DAT_0020);
            DAT_0022._0_1_ = DAT_0027;
            DAT_0022._1_1_ = 10;
            DAT_0024 = 0;
            bStack0000 = 0xc1;
            FUN_d40f();
            DAT_0022._1_1_ = DAT_0020._1_1_;
            bStack0000 = 0xc1;
            FUN_d105(DAT_6f5e);
            bVar1 = *(char *)(DAT_0020 + 10) + DAT_0022._1_1_;
            *(byte *)(DAT_0020 + 10) = bVar1;
            if (0x62 < bVar1) {
              *(undefined1 *)(DAT_0020 + 10) = 99;
            }
            bStack0000 = 0xc1;
            FUN_d152(5);
          }
        }
      }
      else {
        DAT_0022._0_1_ = 10;
        DAT_0022._1_1_ = 0;
        DAT_0024 = 0xe;
        bStack0000 = 0xc0;
        FUN_d36f(DAT_6f5e);
        if (cVar2 != '\0') {
          DAT_0020 = CONCAT11(DAT_0022._1_1_,(byte)DAT_0022);
          DAT_0022._0_1_ = 0;
          DAT_0022._1_1_ = (&DAT_c042)[DAT_6f02];
          bStack0000 = 0xc0;
          FUN_d438();
          DAT_0020 = CONCAT11(DAT_0026,(undefined1)DAT_0020);
          DAT_0022._0_1_ = DAT_0027;
          DAT_0022._1_1_ = 10;
          DAT_0024 = 0;
          bStack0000 = 0xc0;
          FUN_d40f();
          DAT_0022._1_1_ = (byte)DAT_0022 >> 1;
          DAT_0022._0_1_ = DAT_0020._1_1_ >> 1 | (byte)DAT_0022 << 7;
          bStack0000 = 0xc0;
          FUN_d105(DAT_6f5e);
          bStack0000 = 0xc0;
          FUN_c1c0();
          bVar4 = CARRY1(*(byte *)(DAT_0020 + 6),(byte)DAT_0022);
          *(byte *)(DAT_0020 + 6) = *(byte *)(DAT_0020 + 6) + (byte)DAT_0022;
          bVar1 = *(char *)(DAT_0020 + 7) + DAT_0022._1_1_ + bVar4 & 0x7f;
          *(byte *)(DAT_0020 + 7) = bVar1;
          if ((0x26 < bVar1) && (0xf < *(byte *)(DAT_0020 + 6))) {
            *(undefined1 *)(DAT_0020 + 6) = 0xf;
            *(undefined1 *)(DAT_0020 + 7) = 0x27;
          }
          bStack0000 = 0xc0;
          FUN_d152(5);
        }
      }
    }
    cVar2 = '\0';
    if (2 < DAT_6f01) {
      cVar3 = 7 < DAT_6f01;
      cVar2 = '\x01';
      if (!(bool)cVar3) {
        DAT_0022._0_1_ = 10;
        DAT_0022._1_1_ = 0;
        DAT_0024 = 0xe;
        bStack0000 = 0xbf;
        FUN_d36f(DAT_6f5e);
        if (cVar3 != '\0') {
          DAT_0020 = CONCAT11(DAT_0022._1_1_,(byte)DAT_0022);
          DAT_0022._0_1_ = 0;
          DAT_0022._1_1_ = (&DAT_c042)[DAT_6f02];
          bStack0000 = 0xbf;
          FUN_d438();
          DAT_0020 = CONCAT11(DAT_0026,(undefined1)DAT_0020);
          DAT_0022._0_1_ = DAT_0027;
          DAT_0022._1_1_ = 10;
          DAT_0024 = 0;
          bStack0000 = 0xbf;
          FUN_d40f();
          DAT_0022._1_1_ = (byte)DAT_0022;
          DAT_0022._0_1_ = DAT_0020._1_1_;
          bStack0000 = 0xbf;
          FUN_d105(DAT_6f5e);
          bStack0000 = 0xbf;
          FUN_c1a7((byte)DAT_0022);
          bVar4 = CARRY1(*(byte *)(DAT_0020 + 8),(byte)DAT_0022);
          *(byte *)(DAT_0020 + 8) = *(byte *)(DAT_0020 + 8) + (byte)DAT_0022;
          bVar1 = *(char *)(DAT_0020 + 9) + DAT_0022._1_1_ + bVar4 & 3;
          *(byte *)(DAT_0020 + 9) = bVar1;
          if ((2 < bVar1) && (0xe6 < *(byte *)(DAT_0020 + 8))) {
            *(undefined1 *)(DAT_0020 + 8) = 0xe7;
            *(undefined1 *)(DAT_0020 + 9) = 3;
          }
          bStack0000 = 0xbf;
          FUN_d152(5);
        }
        goto code_r0xbec7;
      }
    }
    DAT_0022._0_1_ = 10;
    DAT_0022._1_1_ = 0;
    DAT_0024 = 0xe;
    bStack0000 = 0xbf;
    FUN_d36f(DAT_6f5e);
    if (cVar2 != '\0') {
      DAT_0020 = CONCAT11(DAT_0022._1_1_,(byte)DAT_0022);
      DAT_0022._0_1_ = 0;
      DAT_0022._1_1_ = (&DAT_c042)[DAT_6f02];
      bStack0000 = 0xbf;
      FUN_d438();
      DAT_0020 = CONCAT11(DAT_0026,(undefined1)DAT_0020);
      DAT_0022._0_1_ = DAT_0027;
      DAT_0022._1_1_ = 10;
      DAT_0024 = 0;
      bStack0000 = 0xc0;
      FUN_d40f();
      DAT_0022._1_1_ = (byte)DAT_0022;
      DAT_0022._0_1_ = DAT_0020._1_1_;
      bStack0000 = 0xc0;
      FUN_d105(DAT_6f5e);
      bStack0000 = 0xc0;
      FUN_c1a7((byte)DAT_0022);
      bVar4 = CARRY1(*(byte *)(DAT_0020 + 0xe),(byte)DAT_0022);
      *(byte *)(DAT_0020 + 0xe) = *(byte *)(DAT_0020 + 0xe) + (byte)DAT_0022;
      bVar1 = *(char *)(DAT_0020 + 0xf) + DAT_0022._1_1_ + bVar4 & 3;
      *(byte *)(DAT_0020 + 0xf) = bVar1;
      if ((2 < bVar1) && (0xe6 < *(byte *)(DAT_0020 + 0xe))) {
        *(undefined1 *)(DAT_0020 + 0xe) = 0xe7;
        *(undefined1 *)(DAT_0020 + 0xf) = 3;
      }
      bStack0000 = 0xc0;
      FUN_d152(5);
    }
  } while( true );
}

