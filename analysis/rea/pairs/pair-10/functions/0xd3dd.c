
void FUN_d3dd(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xd3;
  FUN_d105();
  bVar1 = 0;
  do {
    (&DAT_6f73)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x10);
  bVar2 = 0x11;
  bVar1 = 0;
  do {
    if (*(char *)(DAT_0020 + (ushort)bVar2) != -1) {
      (&DAT_6f73)[bVar1] = *(char *)(DAT_0020 + (ushort)bVar2);
      bVar1 = bVar1 + 1;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x1b);
  bVar2 = 0x11;
  bVar1 = 0;
  do {
    *(undefined1 *)(DAT_0020 + (ushort)bVar2) = (&DAT_6f73)[bVar1];
    bVar2 = bVar2 + 1;
    bVar1 = bVar1 + 1;
  } while (bVar2 < 0x1b);
  return;
}

