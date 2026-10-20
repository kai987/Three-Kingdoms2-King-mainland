
byte FUN_ab26(void)

{
  DAT_0018 = (byte)(DAT_000c >> 1 | DAT_000d << 7) >> 3;
  DAT_0019 = (byte)(DAT_000e >> 1 | DAT_000f << 7) >> 3;
  return DAT_000f >> 1;
}

