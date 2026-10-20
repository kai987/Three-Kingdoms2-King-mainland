
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a8d3(void)

{
  *_DAT_0000 = 0x23;
  _DAT_0000[1] = (DAT_000c >> 5) - 0x40;
  _DAT_0000[1] = ((DAT_000e & 0xe0) >> 2) + _DAT_0000[1];
  return;
}

