
void FUN_c917(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xc9;
  FUN_d105(DAT_0036);
  DAT_0028 = 0x11;
  DAT_0029 = 0xff;
  DAT_002a = 0xff;
  DAT_002b = '\0';
  do {
    if ((*(char *)(DAT_0028 + 0x52f) != '\0') && (*(char *)(DAT_0020 + DAT_0028) != -1)) {
      DAT_002b = DAT_002b + '\x01';
      uStack0000 = 0xc9;
      bVar1 = FUN_d2ab(0);
      if (bVar1 < DAT_0029) {
        DAT_002a = DAT_0028;
        DAT_0029 = bVar1;
      }
    }
    bVar1 = DAT_002a;
    DAT_0028 = DAT_0028 + 1;
  } while (DAT_0028 < 0x1b);
  *(undefined1 *)(DAT_002a + 0x52f) = 0;
  DAT_0039 = *(undefined1 *)(DAT_0020 + bVar1);
  uStack0000 = 0xc9;
  uStack0000 = FUN_d2d3(0);
  DAT_0022._0_1_ = FUN_d2ab(DAT_0039,0);
  DAT_0022._1_1_ = uStack0000;
  DAT_0020 = DAT_0020 & 0xff;
  DAT_0024 = 0;
  uStack0000 = 0xc9;
  FUN_d40f();
  return;
}

