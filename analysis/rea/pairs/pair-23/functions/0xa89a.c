
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a89a(void)

{
  *_DAT_0000 = ' ';
  _DAT_0000[1] = DAT_000c >> 3;
  DAT_000f = (DAT_000e >> 7) << 1 | (DAT_000e & 0x78) >> 6;
  _DAT_0000[1] = (DAT_000e & 0xf8) * '\x04' + _DAT_0000[1];
  *_DAT_0000 = *_DAT_0000 + DAT_000f;
  return;
}

