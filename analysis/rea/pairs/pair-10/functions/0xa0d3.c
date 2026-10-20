
void FUN_a0d3(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_f266(0x30);
  DAT_0036 = 0;
  DAT_0037 = '\0';
  DAT_0038 = '\0';
  do {
    DAT_0039 = 0;
    bVar1 = DAT_0036 << 3;
    do {
      if (*(char *)(bVar1 + 0x9d72) < '\0') break;
      uStack0000 = 0xa0;
      DAT_0022._1_1_ = *(char *)(bVar1 + 0x9d72);
      DAT_0024 = bVar1;
      bVar1 = FUN_d105();
      if (((bVar1 & 7) == 7) || ((bVar1 & 7) == DAT_6f03)) {
        DAT_0037 = DAT_0037 + '\x01';
        uStack0000 = 0xa1;
        bVar1 = FUN_d304(DAT_0036);
        if (bVar1 < 4) {
          DAT_0038 = DAT_0038 + '\x01';
          break;
        }
      }
      bVar1 = DAT_0024 + 1;
      DAT_0039 = DAT_0039 + 1;
    } while (DAT_0039 < 8);
    DAT_0036 = DAT_0036 + 1;
    if (0x1d < DAT_0036) {
      return;
    }
  } while( true );
}

