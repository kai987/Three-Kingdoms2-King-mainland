
byte FUN_d64a(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  char cVar4;
  undefined1 uStack0000;
  
  DAT_0013 = DAT_0425;
  DAT_0010 = 0x4c;
  DAT_0011 = 0xd7;
  DAT_0012 = 0;
  uStack0000 = 0xd6;
  FUN_ed19();
  cVar4 = DAT_047b <= DAT_0012;
  if (((DAT_0012 != DAT_047b) && ((bool)cVar4)) &&
     (DAT_0012 = DAT_047b, DAT_0425 = DAT_047b, DAT_0013 != 0)) {
    DAT_0012 = 0;
    DAT_0425 = DAT_0012;
  }
  DAT_0010 = 0x58;
  DAT_0011 = 0xd7;
  DAT_0000 = 0x6e;
  DAT_0001 = 0xd7;
  DAT_047a = DAT_0012;
  uStack0000 = 0xd6;
  FUN_edf5();
  uStack0000 = 0xd6;
  bVar1 = FUN_ddad();
  if (cVar4 != '\0') {
    if (DAT_047c == '\x10') {
      bVar1 = FUN_d7c5();
      return bVar1;
    }
    if ((bool)(DAT_0081 & 1)) {
      if ((DAT_047c == '\x0f') || (DAT_0012 != DAT_047b)) {
        if (DAT_047c == '\x0f') {
          DAT_0481 = (&DAT_0151)[DAT_0012];
          uStack0000 = 0xd7;
          cVar4 = FUN_dd4f(DAT_0402);
          if (cVar4 == DAT_0481) {
            DAT_047c = 0x81;
            return 0x81;
          }
          DAT_047c = 0x80;
          bVar1 = FUN_d7a8();
          return bVar1;
        }
        if ((&DAT_0481)[DAT_0012] == -1) {
          bVar1 = 0;
          if (DAT_047c != '\0') {
            (&DAT_0481)[DAT_0012] = (&DAT_0151)[DAT_0012];
            DAT_047c = DAT_047c + -1;
            uStack0000 = 0xd7;
            bVar1 = FUN_d773(0x3e);
          }
        }
        else {
          (&DAT_0481)[DAT_0012] = 0xff;
          DAT_047c = DAT_047c + '\x01';
          uStack0000 = 0xd7;
          bVar1 = FUN_d773(1);
        }
      }
      else {
        bVar2 = 0;
        bVar3 = 0;
        do {
          bVar1 = (&DAT_0481)[bVar3];
          if (bVar1 != 0xff) {
            (&DAT_0481)[bVar2] = bVar1;
            DAT_0000 = bVar2;
            if (bVar3 != bVar2) {
              bVar1 = 0xff;
              (&DAT_0481)[bVar3] = 0xff;
            }
            bVar2 = bVar2 + 1;
          }
          bVar3 = bVar3 + 1;
        } while (bVar3 < 10);
        if (bVar2 != 0) {
          DAT_047c = 0x81;
          bVar1 = FUN_d7a8();
          return bVar1;
        }
      }
    }
    else {
      bVar1 = DAT_0081 >> 2;
      if ((DAT_0081 >> 1 & 1) != 0) {
        DAT_047c = 0x90;
        bVar1 = FUN_d7a8();
        return bVar1;
      }
    }
  }
  return bVar1;
}

