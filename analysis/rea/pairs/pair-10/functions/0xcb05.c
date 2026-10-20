
void FUN_cb05(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  undefined1 unaff_retaddr;
  
  DAT_002a = 0;
  DAT_002b = 0;
  DAT_0027 = -1;
  do {
    uStack0000 = 0xcb;
    cVar1 = FUN_d105(DAT_002a);
    if (cVar1 == DAT_0040) {
      DAT_0024 = 0x11;
      do {
        if (*(char *)(DAT_0020 + (ushort)DAT_0024) != -1) {
          uStack0000 = 0xcb;
          bVar2 = FUN_d2ab(4);
          if (DAT_002b <= bVar2) {
            DAT_0027 = *(char *)(DAT_0020 + (ushort)DAT_0024);
            DAT_002b = bVar2;
          }
        }
        DAT_0024 = DAT_0024 + 1;
      } while (DAT_0024 < 0x1b);
    }
    DAT_002a = DAT_002a + 1;
  } while (DAT_002a < 0x1e);
  if (DAT_0027 != -1) {
    FUN_cb52(unaff_retaddr);
    return;
  }
  return;
}

