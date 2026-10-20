
void FUN_af30(void)

{
  if (-1 < *(char *)(DAT_0019 + 0x680)) {
    DAT_0002 = DAT_0002 & 0xfc | 2;
  }
  if (-1 < *(char *)(DAT_0019 + 0x6a0)) {
    DAT_0002 = DAT_0002 & 0xf3 | 8;
  }
  if (-1 < *(char *)((byte)(DAT_0019 + 1) + 0x680)) {
    DAT_0002 = DAT_0002 & 0xcf | 0x20;
  }
  if (-1 < *(char *)((byte)(DAT_0019 + 1) + 0x6a0)) {
    DAT_0002 = DAT_0002 & 0x3f | 0x80;
  }
  return;
}

