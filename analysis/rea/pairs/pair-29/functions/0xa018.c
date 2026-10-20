
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_dd8b(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  _DAT_0000 = (undefined1 *)0x6000;
  bVar2 = 0;
  do {
    do {
      *(undefined1 *)((short)_DAT_0000 + (ushort)bVar2) = 0;
      bVar2 = bVar2 + 1;
    } while (bVar2 != 0);
    bVar1 = DAT_0001 + 1;
    _DAT_0000 = (undefined1 *)CONCAT11(bVar1,DAT_0000);
  } while (bVar1 < 0x70);
  do {
    uStack0000 = 0xdd;
    bVar2 = FUN_e87a();
  } while (4 < (bVar2 & 7));
  DAT_6f04 = 0xff;
  DAT_6fe2 = 0xff;
  DAT_0400 = 0xb;
  DAT_0401 = 0;
  uStack0000 = 0xdd;
  DAT_6f45 = bVar2 & 7;
  FUN_f25f(0x30);
  _DAT_0000 = (undefined1 *)0x8c00;
  _DAT_0002 = (undefined1 *)0x6000;
  bVar2 = 0;
  DAT_0004 = 0;
  do {
    *_DAT_0002 = *_DAT_0000;
    if ((char)(DAT_0000 + '\x01') == '\0') {
      DAT_0001 = DAT_0001 + '\x01';
    }
    _DAT_0000 = (undefined1 *)CONCAT11(DAT_0001,DAT_0000 + '\x01');
    if ((char)(DAT_0002 + '\x01') == '\0') {
      DAT_0003 = DAT_0003 + '\x01';
    }
    _DAT_0002 = (undefined1 *)CONCAT11(DAT_0003,DAT_0002 + '\x01');
    bVar2 = bVar2 + 1;
    if (bVar2 == 0) {
      DAT_0004 = DAT_0004 + 1;
    }
  } while ((DAT_0004 < 3) || (bVar2 < 0xc0));
  uStack0000 = 0xde;
  FUN_f25f(0x31);
  _DAT_0000 = &DAT_8000;
  _DAT_0002 = (undefined1 *)0x63c0;
  bVar2 = 0;
  DAT_0004 = 0;
  do {
    *_DAT_0002 = *_DAT_0000;
    if ((char)(DAT_0000 + '\x01') == '\0') {
      DAT_0001 = DAT_0001 + '\x01';
    }
    _DAT_0000 = (undefined1 *)CONCAT11(DAT_0001,DAT_0000 + '\x01');
    if ((char)(DAT_0002 + '\x01') == '\0') {
      DAT_0003 = DAT_0003 + '\x01';
    }
    _DAT_0002 = (undefined1 *)CONCAT11(DAT_0003,DAT_0002 + '\x01');
    bVar2 = bVar2 + 1;
    if (bVar2 == 0) {
      DAT_0004 = DAT_0004 + 1;
    }
  } while ((DAT_0004 < 0xb) || (bVar2 < 0x40));
  DAT_6f00 = 0x59;
  DAT_6f01 = 0;
  DAT_6f83 = 0xff;
  DAT_6f84 = 0xff;
  DAT_6f85 = 0xff;
  DAT_6f86 = 0xff;
  DAT_6f87 = 0xff;
  DAT_6f88 = 0xff;
  DAT_6f89 = 0xff;
  DAT_6f8a = 0;
  return;
}

