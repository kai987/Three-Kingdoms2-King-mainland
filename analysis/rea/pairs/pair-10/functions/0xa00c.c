
void thunk_FUN_d00c(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd0;
  bVar1 = FUN_d2ab((byte)DAT_0020,3);
  DAT_0020._0_1_ = 0x32 - bVar1;
  if (((bVar1 & ((byte)DAT_0020 | 0xcd) | (byte)DAT_0020 & 0xcd) & 0x80) == 0) {
    DAT_0020._0_1_ = ((byte)DAT_0020 ^ 0xff) + 1;
  }
  bVar1 = 0x33 - (byte)DAT_0020;
  if ((((byte)DAT_0020 & (bVar1 | 0xcc) | bVar1 & 0xcc) & 0x80) == 0) {
    bVar1 = 0;
  }
  if (bVar1 < 10) {
    bVar1 = 10;
  }
  *(byte *)(DAT_0022 + 3) = bVar1;
  uStack0000 = 0xd0;
  FUN_d61e();
  return;
}

