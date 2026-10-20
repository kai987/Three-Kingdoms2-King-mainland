
void FUN_c5d2(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xc5;
  FUN_f266(0x31);
  uStack0000 = 0xc5;
  bVar1 = FUN_d105(DAT_0036);
  if ((bVar1 & 7) == DAT_6f03) {
    uStack0000 = 0xc5;
    bVar1 = FUN_d4bb(100);
    if (bVar1 < 10) {
      uStack0000 = 0xc5;
      bVar1 = FUN_d304(DAT_0036);
      if (bVar1 < 10) {
        DAT_0020 = CONCAT11(0x14,DAT_0036);
        uStack0000 = 0xc6;
        FUN_d471();
        DAT_0037 = 0;
        DAT_0022 = CONCAT11(DAT_002b + -0x75 + (0xe3 < DAT_002a),DAT_002a + 0x1c);
        do {
          do {
            DAT_0024 = *(undefined1 *)(DAT_0022 + (ushort)DAT_0037);
            bVar1 = *(char *)(DAT_0022 + (ushort)(byte)(DAT_0037 + 1)) + 0x9c;
            DAT_0020 = CONCAT11(DAT_0020._1_1_,bVar1);
            if (DAT_6f00 < bVar1) {
              DAT_0037 = DAT_0037 + 2;
              return;
            }
            uStack0000 = 0xc6;
            DAT_0037 = DAT_0037 + 2;
            bVar1 = FUN_d283(DAT_0024,0xb);
          } while ((bVar1 & 3) != 1);
          uStack0000 = 0xc6;
          DAT_002a = FUN_c66f(DAT_0024);
          do {
            uStack0000 = 0xc6;
            bVar1 = FUN_e89a();
          } while (99 < bVar1);
        } while (DAT_002a <= bVar1);
        *(byte *)(DAT_0020 + 0xb) = *(byte *)(DAT_0020 + 0xb) & 0xfc | 2;
        uStack0000 = 0xc6;
        FUN_d105(DAT_0036);
        bVar1 = 0x10;
        do {
          bVar1 = bVar1 + 1;
        } while (*(char *)(DAT_0020 + (ushort)bVar1) != -1);
        *(undefined1 *)(DAT_0020 + (ushort)bVar1) = DAT_0024;
        return;
      }
    }
  }
  return;
}

