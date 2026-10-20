
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_af77(char param_1,byte param_2,char param_3)

{
  ushort uVar1;
  char cVar2;
  byte bVar3;
  bool bVar4;
  byte bStack0000;
  
  DAT_0013 = *(char *)(DAT_0010 + (ushort)(byte)(param_3 + 1));
  bStack0000 = param_3 + 2;
  DAT_0012 = param_1;
  region_address(DAT_0402);
  uVar1 = (ushort)bStack0000;
  bStack0000 = bStack0000 + 1;
  _DAT_0017 = (undefined1 *)
              CONCAT11(DAT_0001 + CARRY1(*(byte *)(DAT_0010 + uVar1),DAT_0000),
                       *(byte *)(DAT_0010 + uVar1) + DAT_0000);
  if (DAT_0012 == -0x10) {
    bVar3 = 0;
    DAT_0002 = '\0';
    _DAT_0000 = _DAT_0000 & 0xff;
    do {
      if (_DAT_0017[bVar3] != -1) {
        _DAT_0000 = CONCAT11(DAT_0001 + '\x01',DAT_0000);
      }
      bVar3 = bVar3 + 1;
    } while (bVar3 < 10);
  }
  else if (DAT_0012 == -0xf) {
    _DAT_0000 = CONCAT11(*_DAT_0017,DAT_0000);
    DAT_0002 = _DAT_0017[1];
  }
  else if (DAT_0012 == -0xd) {
    DAT_0002 = 0;
    DAT_0003 = '\0';
    DAT_0004 = 0;
    do {
      if (_DAT_0017[DAT_0004] == -1) break;
      officer_address();
      bVar4 = CARRY1(*(byte *)(_DAT_0000 + 8),DAT_0002);
      DAT_0002 = *(byte *)(_DAT_0000 + 8) + DAT_0002;
      DAT_0003 = *(char *)(_DAT_0000 + 9) + DAT_0003 + bVar4;
      DAT_0004 = DAT_0004 + 1;
    } while (DAT_0004 < 10);
    _DAT_0000 = CONCAT11(DAT_0002,DAT_0000);
    DAT_0002 = DAT_0003;
  }
  else {
    _DAT_0000 = CONCAT11(*_DAT_0017,DAT_0000);
    DAT_0002 = '\0';
  }
  DAT_0003 = 0;
  FUN_e9ba();
  cVar2 = bStack0000;
  _DAT_0017 = (undefined1 *)CONCAT11(DAT_0018,0xb6);
  DAT_0016 = 1;
  if (DAT_0013 != '\x02') {
    if (DAT_0013 != '\x03') {
      if (DAT_0013 != '\x04') {
        if (DAT_0013 != '\x05') {
          bStack0000 = 0xb0;
          FUN_b091(DAT_0009 >> 4,cVar2);
        }
        bStack0000 = 0xb0;
        FUN_b091(DAT_0009 & 0xf);
      }
      bStack0000 = 0xb0;
      FUN_b091(DAT_0008 >> 4);
    }
    bStack0000 = 0xb0;
    FUN_b091(DAT_0008 & 0xf);
  }
  bStack0000 = 0xb0;
  FUN_b091(DAT_0007 >> 4);
  DAT_0016 = DAT_0017;
  if ((DAT_0007 & 0xf) == 0) {
    (&DAT_0160)[param_2] = DAT_0017;
  }
  else {
    (&DAT_0160)[param_2] = (DAT_0007 & 0xf) + DAT_0017;
    DAT_0016 = DAT_0017;
  }
  return;
}

