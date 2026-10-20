
void FUN_c1a7(byte param_1)

{
  byte bVar1;
  
  DAT_002a = '\x01';
  if (0x1e < param_1) {
    DAT_002a = '\x02';
  }
  bVar1 = *(char *)(DAT_0020 + 0xb) + DAT_002a;
  if (99 < bVar1) {
    bVar1 = 100;
  }
  *(byte *)(DAT_0020 + 0xb) = bVar1;
  return;
}

