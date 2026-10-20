
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b1b0(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  if ((DAT_0022 == 1) || (DAT_0022 == 5)) {
    cVar1 = '\x12';
  }
  else if ((DAT_0022 == 2) || (DAT_0022 == 4)) {
    cVar1 = '$';
  }
  else {
    cVar1 = '\0';
  }
  cVar1 = cVar1 + DAT_0020;
  _DAT_0020 = (undefined1 *)CONCAT11(DAT_0021,cVar1);
  if (DAT_6f94 != '\0') {
    bVar2 = (DAT_6f94 + -1) * '\x02' + cVar1;
    _DAT_0020 = (undefined1 *)CONCAT11((2 < bVar2) + -0x4d,bVar2 - 3);
    bVar2 = 0;
    if (DAT_6f91 != 0) {
      bVar2 = 4;
    }
    bVar3 = 0;
    do {
      DAT_0022 = *(byte *)((short)_DAT_0020 + (ushort)bVar3);
      (&DAT_6f99)[bVar2] = DAT_0022 >> 4;
      *(byte *)(bVar2 + 0x6f9a) = DAT_0022 & 0xf;
      bVar2 = bVar2 + 2;
      bVar3 = bVar3 + 1;
    } while (bVar3 < 2);
    bVar2 = 0;
    if (DAT_6f91 != 0) {
      bVar2 = 4;
    }
    DAT_0022 = bVar2 + 4;
    _DAT_0020 = (undefined1 *)CONCAT11(DAT_0021,1);
    bVar3 = DAT_6f91 + 1;
    do {
      if ((&DAT_6f99)[bVar2] != '\0') {
        _DAT_0020 = (undefined1 *)CONCAT11((&DAT_6f99)[bVar2],DAT_0020);
        do {
          (&DAT_6fa1)[bVar3] = DAT_0020;
          bVar3 = bVar3 + 1;
          cVar1 = DAT_0021 + -1;
          _DAT_0020 = (undefined1 *)CONCAT11(cVar1,DAT_0020);
        } while (cVar1 != '\0');
      }
      _DAT_0020 = (undefined1 *)CONCAT11(DAT_0021,DAT_0020 + '\x01');
      bVar2 = bVar2 + 1;
    } while (bVar2 < DAT_0022);
  }
  if (DAT_6f91 == 0) {
    uStack0000 = 0xb2;
    FUN_b2ae();
  }
  else {
    uStack0000 = 0xb2;
    FUN_b312();
  }
  bVar2 = DAT_6f91;
  DAT_002a = DAT_6f91 + 10;
  *(undefined1 *)(DAT_6f91 + 0x614) = *_DAT_0020;
  *(undefined1 *)(bVar2 + 0x600) = _DAT_0020[1];
  bVar2 = bVar2 + 1;
  do {
    if ((&DAT_6fa1)[bVar2] == -1) {
      return;
    }
    DAT_002b = (&DAT_6fa1)[bVar2] - 1;
    bVar3 = *(byte *)(DAT_002b + 0x22);
    *(undefined1 *)(bVar2 + 0x614) = _DAT_0020[bVar3];
    *(undefined1 *)(bVar2 + 0x600) = _DAT_0020[(byte)(bVar3 + 1)];
    *(char *)(DAT_002b + 0x22) = *(char *)(DAT_002b + 0x22) + '\x02';
    bVar2 = bVar2 + 1;
  } while (bVar2 < DAT_002a);
  return;
}

