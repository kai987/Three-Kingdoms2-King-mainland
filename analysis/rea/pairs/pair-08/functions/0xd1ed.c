
void FUN_d1ed(void)

{
  ushort uVar1;
  byte bVar2;
  byte bVar3;
  byte bStack0000;
  
  if ((DAT_008f == '\0') && (DAT_0500 < 0xc)) {
    bStack0000 = 0xd1;
    FUN_d2f5();
    if (DAT_0061 != '\a') {
      bStack0000 = 0xd2;
      FUN_f25f(0x31);
      bVar3 = (DAT_050e & 0x7f) >> 6;
      bVar2 = DAT_050e << 2;
      DAT_000a = *(undefined1 *)(bVar2 + 0x9d58);
      DAT_000b = *(undefined1 *)(bVar2 + 0x9d59);
      DAT_000c = *(char *)(bVar2 + 0x9d5a);
      DAT_000d = *(undefined1 *)(bVar2 + 0x9d5b);
      bStack0000 = 0xd2;
      FUN_d337();
      if (bVar3 != 0) {
        DAT_0000 = 0x15;
        DAT_0001 = 0xd3;
        DAT_0002 = 0;
        DAT_0003 = 0;
        DAT_0004 = 0x9c;
        bStack0000 = 0xd2;
        FUN_f09c();
      }
      bStack0000 = 0xd2;
      FUN_f25f(0x31);
      bStack0000 = DAT_050e * '\x06';
      if (-1 < *(char *)(bStack0000 + 0x9ba4)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba5);
        DAT_000c = *(char *)(bStack0000 + 0x9ba4);
        FUN_d296();
      }
      if (-1 < *(char *)(bStack0000 + 0x9ba6)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba7);
        DAT_000c = *(char *)(bStack0000 + 0x9ba6);
        FUN_d296();
      }
      uVar1 = (ushort)bStack0000;
      if (-1 < *(char *)(uVar1 + 0x9ba8)) {
        DAT_000a = *(undefined1 *)(bStack0000 + 0x9ba9);
        bStack0000 = 0xd2;
        DAT_000c = *(char *)(uVar1 + 0x9ba8);
        FUN_d296();
      }
      return;
    }
  }
  return;
}

