
byte FUN_d1a4(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_002a = DAT_6f03;
  uStack0000 = 0xd1;
  FUN_f266(0x30);
  bVar1 = 0xf;
  do {
    (&DAT_6f73)[bVar1] = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  DAT_002b = 0;
  DAT_002c = 0;
  bVar1 = DAT_0036 << 3;
  do {
    if (*(char *)(bVar1 + 0x9d72) < '\0') {
      return DAT_002b;
    }
    uStack0000 = 0xd1;
    DAT_0022._1_1_ = *(char *)(bVar1 + 0x9d72);
    DAT_0024 = bVar1;
    bVar1 = FUN_d105();
    if (((bVar1 & 7) != 7) && ((bVar1 & 7) != DAT_002a)) {
      (&DAT_6f73)[DAT_002b] = DAT_0022._1_1_;
      DAT_002b = DAT_002b + 1;
    }
    bVar1 = DAT_0024 + 1;
    DAT_002c = DAT_002c + 1;
  } while (DAT_002c < 8);
  return DAT_002b;
}

