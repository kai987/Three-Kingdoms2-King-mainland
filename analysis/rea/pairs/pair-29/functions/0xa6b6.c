
void FUN_a6b6(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0002 = 0x9b < DAT_6f00;
  DAT_0001 = DAT_6f00 + 100;
  DAT_0003 = 0;
  uStack0000 = 0xa6;
  FUN_e9ba();
  DAT_0383 = (DAT_0008 & 0xf) + 4;
  DAT_038d = (DAT_0008 & 0xf) + 0x14;
  DAT_0384 = (DAT_0007 >> 4) + 4;
  DAT_038e = (DAT_0007 >> 4) + 0x14;
  DAT_0385 = (DAT_0007 & 0xf) + 4;
  DAT_038f = (DAT_0007 & 0xf) + 0x14;
  DAT_0001 = DAT_6f01 + '\x01';
  DAT_0002 = 0;
  DAT_0003 = 0;
  uStack0000 = 0xa7;
  FUN_e9ba();
  bVar1 = DAT_0007 >> 4;
  if (bVar1 == 0) {
    bVar1 = 0xe;
  }
  DAT_0388 = bVar1 + 4;
  DAT_0392 = bVar1 + 0x14;
  DAT_0389 = (DAT_0007 & 0xf) + 4;
  DAT_0393 = (DAT_0007 & 0xf) + 0x14;
  DAT_0380 = 7;
  DAT_0381 = 0x20;
  DAT_0382 = 0x43;
  DAT_038a = 7;
  DAT_038b = 0x20;
  DAT_038c = 99;
  DAT_0387 = 0x12;
  DAT_0391 = 0x22;
  DAT_0386 = 0xe;
  DAT_0390 = 0x1e;
  DAT_0394 = 0xff;
  DAT_007e = DAT_007e | 4;
  return;
}

