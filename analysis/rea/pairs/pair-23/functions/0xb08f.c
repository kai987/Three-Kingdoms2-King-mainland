
byte FUN_b08f(void)

{
  DAT_0018 = ((byte)(DAT_000c >> 1 | DAT_000d << 7) >> 4) << 1;
  DAT_0019 = ((byte)(DAT_000e >> 1 | DAT_000f << 7) >> 4) << 1;
  DAT_0016 = ((byte)(DAT_001c >> 1 | DAT_001d << 7) >> 4) << 1;
  DAT_0017 = ((byte)(DAT_000e >> 1 | DAT_000f << 7) >> 4) << 1;
  return DAT_000f >> 1;
}

