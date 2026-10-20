
char FUN_d304(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xd3;
  FUN_d105();
  cVar1 = '\0';
  bVar2 = 0x11;
  do {
    if (*(char *)(DAT_0020 + (ushort)bVar2) == -1) {
      return cVar1;
    }
    cVar1 = cVar1 + '\x01';
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x1b);
  return cVar1;
}

