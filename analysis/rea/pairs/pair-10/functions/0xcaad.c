
void FUN_caad(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  undefined1 in_stack_00000004;
  
  DAT_002a = 0;
  do {
    uStack0000 = 0xca;
    cVar1 = FUN_d105(DAT_002a);
    if (cVar1 == DAT_0040) {
      bVar2 = 0x11;
      do {
        if (*(char *)(DAT_0020 + (ushort)bVar2) == DAT_0027) {
          FUN_cb52(in_stack_00000004);
          return;
        }
        bVar2 = bVar2 + 1;
      } while (bVar2 < 0x1b);
    }
    DAT_002a = DAT_002a + 1;
  } while (DAT_002a < 0x1e);
  return;
}

