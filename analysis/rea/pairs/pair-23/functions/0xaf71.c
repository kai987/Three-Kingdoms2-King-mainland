
void FUN_af71(void)

{
  if (-1 < *(char *)(DAT_0019 + 0x6c0)) {
    DAT_0003 = DAT_0003 & 0xfc | 2;
  }
  if (-1 < *(char *)(DAT_0019 + 0x6e0)) {
    DAT_0003 = DAT_0003 & 0xf3 | 8;
  }
  if (-1 < *(char *)((byte)(DAT_0019 + 1) + 0x6c0)) {
    DAT_0003 = DAT_0003 & 0xcf | 0x20;
  }
  if (-1 < *(char *)((byte)(DAT_0019 + 1) + 0x6e0)) {
    DAT_0003 = DAT_0003 & 0x3f | 0x80;
  }
  DAT_0017 = DAT_0017 + -1;
  return;
}

