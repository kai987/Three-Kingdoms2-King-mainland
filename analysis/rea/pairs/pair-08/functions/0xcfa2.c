
void FUN_cfa2(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  if ((((DAT_008f == '\0') && (DAT_04c8 == '\0')) && (DAT_0500 < 0xc)) && ((DAT_005e & 0x20) != 0))
  {
    DAT_000a = 0x20;
    DAT_000c = 0xb0;
    DAT_0000 = 0x3c;
    DAT_0001 = 0xd1;
    DAT_0002 = 0;
    uStack0000 = 0xcf;
    FUN_f1ad();
    DAT_0000 = 0x5d;
    if ((DAT_005e & 0x40) == 0) {
      DAT_0000 = 0x6e;
    }
    DAT_0001 = 0xd1;
    uStack0000 = 0xcf;
    FUN_f1ad();
    DAT_0001 = DAT_0505;
    DAT_0002 = 0;
    DAT_0003 = 0;
    uStack0000 = 0xd0;
    FUN_e9ba();
    if (DAT_0007 >> 4 != 0) {
      DAT_000a = 0x20;
      DAT_000c = 0xe0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = 0x20;
    DAT_000c = 0xe8;
    uStack0000 = 0xd0;
    FUN_d126(DAT_0007 & 0xf);
    DAT_0001 = DAT_0506;
    DAT_0002 = 0;
    DAT_0003 = 0;
    uStack0000 = 0xd0;
    FUN_e9ba();
    if (DAT_0007 >> 4 != 0) {
      DAT_000a = 0x10;
      DAT_000c = 0xd0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = 0x10;
    DAT_000c = 0xd8;
    uStack0000 = 0xd0;
    FUN_d126(DAT_0007 & 0xf);
    if ((DAT_005e & 0x40) == 0) {
      bVar1 = 0;
      if (DAT_0504 < '\0') {
        bVar1 = 2;
      }
      DAT_0001 = (&DAT_0522)[bVar1];
      DAT_0002 = (&DAT_0523)[bVar1];
      DAT_0003 = 0;
      uStack0000 = 0xd0;
      FUN_e9ba();
    }
    else {
      bVar1 = 0;
      if (DAT_0504 < '\0') {
        bVar1 = 2;
      }
      DAT_0001 = *(undefined1 *)(bVar1 + 0x526);
      DAT_0002 = *(undefined1 *)(bVar1 + 0x527);
      DAT_0003 = 0;
      uStack0000 = 0xd0;
      FUN_e9ba();
    }
    DAT_0011 = '\0';
    DAT_0010 = 0x40;
    if (DAT_0008 >> 4 != 0) {
      DAT_0011 = '\x01';
      DAT_000a = 0x40;
      DAT_000c = 0xd0;
      uStack0000 = 0xd0;
      FUN_d126(DAT_0008 >> 4);
    }
    if (((DAT_0008 & 0xf) != 0) || (DAT_0011 != '\0')) {
      DAT_0011 = DAT_0011 + '\x01';
      DAT_000a = DAT_0010;
      DAT_000c = 0xd8;
      uStack0000 = 0xd0;
      FUN_d126();
    }
    if ((DAT_0007 >> 4 != 0) || (DAT_0011 != '\0')) {
      DAT_000a = DAT_0010;
      DAT_000c = 0xe0;
      uStack0000 = 0xd1;
      FUN_d126(DAT_0007 >> 4);
    }
    DAT_000a = DAT_0010;
    DAT_000c = 0xe8;
    uStack0000 = 0xd1;
    FUN_d126(DAT_0007 & 0xf);
    return;
  }
  return;
}

