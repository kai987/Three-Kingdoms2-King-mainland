
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte FUN_c6cc(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  byte unaff_retaddr;
  
  uStack0000 = 0xc6;
  bVar1 = FUN_d105(DAT_0036);
  bVar1 = bVar1 & 7;
  if (bVar1 == DAT_6f03) {
    uStack0000 = 0xc6;
    bVar1 = FUN_d4bb(100);
    if (bVar1 < (byte)(&DAT_c795)[DAT_6f02]) {
      uStack0000 = 0xc6;
      bVar1 = FUN_d304(DAT_0036);
      if (bVar1 < 10) {
        DAT_0037 = 0;
        uStack0000 = 0xc6;
        FUN_f266(0x30);
        bVar1 = 0xf;
        do {
          (&DAT_6f73)[bVar1] = 0xff;
          bVar1 = bVar1 - 1;
        } while (-1 < (char)bVar1);
        bVar1 = DAT_0036 << 3;
        bVar2 = 0;
        do {
          (&DAT_6f73)[bVar2] = *(undefined1 *)(bVar1 + 0x9d72);
          bVar1 = bVar1 + 1;
          bVar2 = bVar2 + 1;
        } while (bVar2 < 8);
        DAT_0022 = 0x63c0;
        bVar1 = 0;
        do {
          if ((*(byte *)(DAT_0022 + 0xb) & 3) == 0) {
            uStack0000 = 199;
            DAT_002a = FUN_c66f(bVar1);
            do {
              uStack0000 = 199;
              bVar2 = FUN_e89a();
            } while (99 < bVar2);
            if (bVar2 < DAT_002a) {
              if (*(char *)(DAT_0022 + 5) == DAT_0036) {
LAB_c765:
                *(byte *)(DAT_0022 + 0xb) = *(byte *)(DAT_0022 + 0xb) & 0xfc | 2;
                uStack0000 = 199;
                FUN_d105(DAT_0036);
                bVar2 = 0x10;
                do {
                  bVar2 = bVar2 + 1;
                } while (*(char *)(DAT_0020 + (ushort)bVar2) != -1);
                *(byte *)(DAT_0020 + (ushort)bVar2) = bVar1;
                uStack0000 = 199;
                DAT_0031 = bVar1;
                FUN_d319(DAT_6f03);
                DAT_0030 = *_DAT_0024;
                uStack0000 = 199;
                FUN_cf3f();
                return unaff_retaddr;
              }
              bVar2 = 0;
              do {
                if (*(char *)(DAT_0022 + 5) == (&DAT_6f73)[bVar2]) goto LAB_c765;
                bVar2 = bVar2 + 1;
              } while (bVar2 < 8);
            }
          }
          bVar2 = DAT_0022._1_1_ + (0xf3 < (byte)DAT_0022);
          DAT_0022 = CONCAT11(bVar2,(byte)DAT_0022 + 0xc);
          bVar1 = bVar1 + 1;
          if (0xec < bVar1) {
            return bVar2;
          }
        } while( true );
      }
    }
  }
  return bVar1;
}

