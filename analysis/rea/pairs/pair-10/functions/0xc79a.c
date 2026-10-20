
void FUN_c79a(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  DAT_0036 = 0xff;
  do {
    do {
      DAT_0036 = DAT_0036 + 1;
      if (0x1d < DAT_0036) {
        return;
      }
      uStack0000 = 199;
      bVar1 = FUN_d105(DAT_0036);
    } while ((bVar1 & 7) != DAT_6f03);
    bVar1 = 0xf;
    do {
      (&DAT_0540)[bVar1] = 0xff;
      bVar1 = bVar1 - 1;
    } while (-1 < (char)bVar1);
    while( true ) {
      uStack0000 = 199;
      FUN_c917();
      if (((char)DAT_0022 != '\0') || (DAT_002b < 2)) break;
      uStack0000 = 199;
      bVar1 = FUN_e88a();
      cVar2 = DAT_0020._1_1_ <= bVar1;
      if ((bool)cVar2) {
        DAT_0022._0_1_ = '\x14';
        DAT_0022._1_1_ = 0;
        DAT_0024 = 0;
        uStack0000 = 199;
        FUN_d36f(DAT_0036);
        if (cVar2 == '\0') {
          return;
        }
        uStack0000 = 199;
        FUN_f266(0x30);
        if ((*(byte *)(DAT_0036 + 0x8ffc) & 8) == 0) {
          uStack0000 = 199;
          FUN_c80a();
        }
        else {
          uStack0000 = 200;
          FUN_c97a();
          uStack0000 = 200;
          FUN_d165(5);
        }
      }
    }
  } while( true );
}

