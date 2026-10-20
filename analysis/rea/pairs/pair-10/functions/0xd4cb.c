
void FUN_d4cb(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  bVar1 = 0x7f;
  do {
    *(undefined1 *)(bVar1 + 0x580) = 0;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xd4;
  FUN_f266(0x30);
  DAT_0036 = '\x1d';
  do {
    uStack0000 = 0xd4;
    bVar1 = FUN_d105(DAT_0036);
    if ((bVar1 & 7) == DAT_6f03) {
      for (DAT_0024 = DAT_0036 << 3; -1 < (char)*(byte *)(DAT_0024 + 0x9d72);
          DAT_0024 = DAT_0024 + 1) {
        uStack0000 = 0xd5;
        DAT_0025 = *(byte *)(DAT_0024 + 0x9d72);
        bVar1 = FUN_d105();
        if ((bVar1 & 7) == DAT_6f03) {
          *(byte *)((byte)(DAT_0036 + (&DAT_d5bf)[DAT_0025]) + 0x580) =
               (&DAT_d5df)[DAT_0025 & 7] |
               *(byte *)((byte)(DAT_0036 + (&DAT_d5bf)[DAT_0025]) + 0x580);
        }
      }
    }
    DAT_0036 = DAT_0036 + -1;
  } while (-1 < DAT_0036);
  bVar2 = 1;
  bVar1 = 0;
  do {
    do {
      uStack0000 = 0xd5;
      FUN_d53e();
      bVar2 = bVar2 + 1;
    } while (bVar2 < 0x1e);
    bVar2 = bVar1 + 1;
    bVar1 = bVar1 + 2;
  } while (bVar1 < 0x1d);
  return;
}

