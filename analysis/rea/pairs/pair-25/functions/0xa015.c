
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_b7d9(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xb7;
  region_address(DAT_0471);
  bVar4 = 2;
  bVar3 = 0x26;
  do {
    (&DAT_0500)[bVar3] = _DAT_0000[bVar4];
    _DAT_0000[bVar4] = 0;
    bVar4 = bVar4 + 1;
    bVar3 = bVar3 + 1;
    if (bVar3 == 0x28) {
      bVar3 = 0x22;
    }
  } while (bVar4 < 6);
  DAT_0507 = *_DAT_0000;
  _DAT_0000 = (byte *)CONCAT11(DAT_0001 + (0xee < DAT_0000),DAT_0000 + 0x11);
  bVar3 = 9;
  do {
    *(byte *)(bVar3 + 0x664) = _DAT_0000[bVar3];
    _DAT_0000[bVar3] = -1;
    bVar3 = bVar3 - 1;
  } while (-1 < (char)bVar3);
  DAT_066e = DAT_0481;
  bVar4 = 0xb;
  bVar3 = 0;
  do {
    if (bVar3 < 10) {
      cVar2 = (&DAT_0151)[bVar3];
      if (cVar2 != DAT_0481) goto LAB_b83a;
    }
    else {
      cVar2 = -1;
LAB_b83a:
      *(char *)(bVar4 + 0x664) = cVar2;
      bVar4 = bVar4 + 1;
    }
    bVar3 = bVar3 + 1;
  } while (bVar4 < 0x14);
  uStack0000 = 0xb8;
  region_address(DAT_0402);
  DAT_0507 = *_DAT_0000 << 4 | DAT_0507;
  bVar3 = 0;
  do {
    if ((&DAT_0151)[bVar3] == -1) break;
    for (bVar4 = 0x11; _DAT_0000[bVar4] != (&DAT_0151)[bVar3]; bVar4 = bVar4 + 1) {
    }
    _DAT_0000[bVar4] = -1;
    bVar3 = bVar3 + 1;
  } while (bVar3 < 10);
  bVar3 = 0x11;
  DAT_0003 = 0x10;
  do {
    DAT_0002 = _DAT_0000[bVar3];
    _DAT_0000[bVar3] = -1;
    if (DAT_0002 != -1) {
      DAT_0003 = DAT_0003 + 1;
      _DAT_0000[DAT_0003] = DAT_0002;
    }
    bVar3 = bVar3 + 1;
  } while (bVar3 < 0x1b);
  if (_DAT_0000[0x11] == -1) {
    *_DAT_0000 = '\a';
  }
  bVar1 = _DAT_0000[2] - DAT_042f;
  bVar3 = ~_DAT_0000[2];
  bVar4 = DAT_042f & (bVar3 | bVar1);
  _DAT_0000[2] = bVar1;
  _DAT_0000[3] = (_DAT_0000[3] - DAT_0430) - (((bVar4 | bVar1 & bVar3) & 0x80) == 0);
  bVar1 = _DAT_0000[4] - DAT_0432;
  bVar3 = ~_DAT_0000[4];
  bVar4 = DAT_0432 & (bVar3 | bVar1);
  _DAT_0000[4] = bVar1;
  _DAT_0000[5] = (_DAT_0000[5] - DAT_0433) - (((bVar4 | bVar1 & bVar3) & 0x80) == 0);
  return;
}

