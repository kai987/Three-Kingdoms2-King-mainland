
void FUN_c1c0(void)

{
  byte bVar1;
  
  DAT_002a = '\x01';
  if (((DAT_0022._1_1_ - 0xb) -
       (((~(byte)DAT_0022 & 0xb8 | (byte)DAT_0022 + 0x48 & 0xb8 |
         (byte)DAT_0022 + 0x48 & ~(byte)DAT_0022) & 0x80) == 0) & ~DAT_0022._1_1_ & 0x80) != 0) {
    DAT_002a = '\x02';
  }
  bVar1 = *(char *)(DAT_0020 + 0xb) + DAT_002a;
  if (99 < bVar1) {
    bVar1 = 100;
  }
  *(byte *)(DAT_0020 + 0xb) = bVar1;
  return;
}

