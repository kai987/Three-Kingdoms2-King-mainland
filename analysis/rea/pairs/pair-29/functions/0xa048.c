
void FUN_a048(void)

{
  ushort uVar1;
  char cVar2;
  byte bVar3;
  
  if ((DAT_007e & 4) != 0) {
    return;
  }
  if ((DAT_0303 == '\0') && (DAT_0308 == '\0')) {
    if ((DAT_005e & DAT_0305) != 0) {
      FUN_ee72();
      return;
    }
    if (*(char *)(DAT_0304 + 0x34e) != -0x80) {
      DAT_2007 = *(undefined1 *)(DAT_0304 + 0x31e);
      cVar2 = DAT_031c;
      if (DAT_030c == '\0') {
        DAT_2007 = *(undefined1 *)(DAT_0304 + 0x34e);
        cVar2 = DAT_034c;
      }
      DAT_2006 = cVar2 + DAT_0304;
      DAT_0304 = DAT_0304 + 1;
      return;
    }
  }
  else {
    DAT_2006 = DAT_031c;
    for (bVar3 = 0; uVar1 = (ushort)bVar3, *(char *)(uVar1 + 0x31e) != -0x80; bVar3 = bVar3 + 1) {
      DAT_2007 = *(char *)(uVar1 + 0x31e);
    }
    if (DAT_030c == '\0') {
      DAT_2006 = DAT_034c;
      for (bVar3 = 0; uVar1 = (ushort)bVar3, *(char *)(uVar1 + 0x34e) != -0x80; bVar3 = bVar3 + 1) {
        DAT_2007 = *(char *)(uVar1 + 0x34e);
      }
    }
  }
  DAT_0304 = 0xff;
  DAT_007e = DAT_007e & 0xfe;
  return;
}

