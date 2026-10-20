
void thunk_FUN_da02(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  DAT_001f = 3;
  DAT_0014 = DAT_048e;
  DAT_0015 = DAT_048f;
  cVar3 = -((char)DAT_0081 >> 7);
  bVar1 = DAT_048b;
  if (cVar3 == '\0') {
    if ((char)(DAT_0081 << 1) < '\0') {
      cVar3 = 2 < DAT_048b;
      if (DAT_048b != 3) {
        DAT_048b = DAT_048b + 1;
      }
    }
    else {
      if ((char)(DAT_0081 << 2) < '\0') {
        uStack0000 = 0xda;
        FUN_db09();
        bVar1 = DAT_048e - DAT_0000;
        DAT_048f = (DAT_048f - DAT_0001) -
                   (((DAT_0000 & (~DAT_048e | bVar1) | bVar1 & ~DAT_048e) & 0x80) == 0);
        DAT_048e = bVar1;
      }
      else {
        bVar1 = DAT_0081 << 4;
        cVar3 = '\0';
        if (-1 < (char)(DAT_0081 << 3)) goto LAB_da91;
        uStack0000 = 0xda;
        FUN_db09(bVar1);
        bVar4 = CARRY1(DAT_048e,DAT_0000);
        DAT_048e = DAT_048e + DAT_0000;
        DAT_048f = DAT_048f + DAT_0001 + bVar4;
      }
      DAT_0000 = DAT_048e;
      DAT_0001 = DAT_048f;
      bVar1 = (DAT_0491 - DAT_048f) -
              (((DAT_048e & (~DAT_0490 | DAT_0490 - DAT_048e) | DAT_0490 - DAT_048e & ~DAT_0490) &
               0x80) == 0);
      cVar3 = ((DAT_048f & (~DAT_0491 | bVar1) | bVar1 & ~DAT_0491) & 0x80) != 0;
      if (!(bool)cVar3) {
        DAT_048e = DAT_0014;
        DAT_048f = DAT_0015;
        bVar1 = DAT_0015;
      }
    }
  }
  else if (DAT_048b != 0) {
    DAT_048b = DAT_048b - 1;
  }
LAB_da91:
  uStack0000 = 0xda;
  FUN_ddad(bVar1);
  if (cVar3 != '\0') {
    DAT_0013 = DAT_0081 & 3;
    DAT_0001 = DAT_048e;
    DAT_0002 = DAT_048f;
    DAT_0003 = 0;
    uStack0000 = 0xda;
    FUN_e9ba();
    DAT_048c = DAT_0007;
    DAT_048d = DAT_0008;
    DAT_0011 = '\x03' - DAT_048b;
    DAT_0010 = 1;
    bVar2 = 2;
    bVar1 = 0;
    do {
      uStack0000 = 0xda;
      FUN_db35((byte)(&DAT_048b)[bVar2] >> 4);
      if (bVar2 == 1) {
        DAT_0010 = 0x76;
      }
      uStack0000 = 0xda;
      FUN_db35((&DAT_048b)[bVar2] & 0xf);
      bVar2 = bVar2 - 1;
    } while (bVar2 != 0);
    (&DAT_031e)[bVar1] = 0x80;
    DAT_0303 = 1;
    DAT_030c = 1;
    DAT_046c = DAT_046c + '\x01';
    DAT_007e = DAT_007e | 1;
  }
  return;
}

