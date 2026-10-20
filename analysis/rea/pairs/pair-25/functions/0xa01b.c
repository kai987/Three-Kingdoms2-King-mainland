
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_b964(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xb9;
  FUN_f25f(0x31);
  _DAT_0000 = (ushort)DAT_0402;
  _DAT_0002 = 0x1400;
  uStack0000 = 0xb9;
  FUN_ebe9();
  _DAT_0002 = CONCAT11(DAT_0007 + -0x75 + (0xe3 < DAT_0006),DAT_0006 + 0x1c);
  DAT_0004 = 0;
  do {
    DAT_0472 = *(byte *)(_DAT_0002 + (ushort)DAT_0004);
    if (DAT_0472 == 0xff) {
LAB_b9ea:
      uStack0000 = 0xb9;
      FUN_f25f(0x30);
      bVar2 = DAT_0402 << 3;
      bVar1 = 0;
      do {
        (&DAT_0160)[bVar1] = *(undefined1 *)(bVar2 + 0x9d72);
        bVar2 = bVar2 + 1;
        bVar1 = bVar1 + 1;
      } while (bVar1 < 8);
      uStack0000 = 0xba;
      FUN_f25f(0x31);
      DAT_0004 = 0;
      do {
        uStack0000 = 0xba;
        officer_address(DAT_0004);
        if ((*(byte *)(_DAT_0000 + 0xb) & 3) == 0) {
          DAT_0472 = DAT_0004;
          bVar2 = *(byte *)(_DAT_0000 + 5);
          if (bVar2 == DAT_0402) {
            DAT_0472 = DAT_0004;
            return;
          }
          bVar1 = 0;
          do {
            if ((&DAT_0160)[bVar1] == bVar2) {
              DAT_0005 = bVar2;
              DAT_0472 = DAT_0004;
              return;
            }
            bVar1 = bVar1 + 1;
            DAT_0005 = bVar2;
          } while (bVar1 < 8);
        }
        DAT_0004 = DAT_0004 + 1;
      } while (DAT_0004 < 0xed);
      DAT_0010._1_1_ = 0x80;
      return;
    }
    uStack0000 = 0xb9;
    officer_address();
    if ((*(byte *)(_DAT_0000 + 0xb) & 3) == 1) {
      DAT_0004 = DAT_0004 + 1;
      bVar2 = *(char *)(_DAT_0002 + (ushort)DAT_0004) + 0x9c;
      if ((bVar2 == DAT_6f00) || (bVar2 < DAT_6f00)) {
        bVar2 = 0;
        do {
          if ((&DAT_ba50)[bVar2] == DAT_0472) {
            DAT_0473 = (&DAT_ba50)[(byte)(bVar2 + 1)];
            DAT_0470 = 7;
            return;
          }
          bVar2 = bVar2 + 2;
        } while (bVar2 < 0x24);
        return;
      }
      goto LAB_b9ea;
    }
    DAT_0004 = DAT_0004 + 2;
  } while( true );
}

