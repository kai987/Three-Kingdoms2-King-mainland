
void FUN_c3ff(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_0037 = 0x11;
  DAT_0038 = -1;
  DAT_0039 = 0;
  do {
    uStack0000 = 0xc4;
    FUN_d105(DAT_6f5e);
    if (*(char *)(DAT_0020 + (ushort)DAT_0037) != -1) {
      uStack0000 = 0xc4;
      DAT_003b = *(char *)(DAT_0020 + (ushort)DAT_0037);
      cVar1 = FUN_c451();
      if (cVar1 != -1) {
        uStack0000 = 0xc4;
        DAT_003c = cVar1;
        bVar2 = FUN_d2ab(DAT_003b,1);
        if (DAT_0039 <= bVar2) {
          DAT_0038 = DAT_003b;
          DAT_003a = DAT_003c;
          DAT_0039 = bVar2;
        }
      }
    }
    DAT_0037 = DAT_0037 + 1;
  } while (DAT_0037 < 0x1b);
  return;
}

