
void FUN_ac80(byte param_1)

{
  if ((char)(DAT_009c << 1) < '\0') {
    if ((DAT_000c & 0x10) != 0) {
      if (DAT_0006 == '\b') {
        DAT_0002 = DAT_0002 & 0xc;
        DAT_018a = DAT_0003 & 3 | DAT_0002 | DAT_018a & 0xf0;
        return;
      }
      DAT_0002 = DAT_0002 & 0xcc;
      (&DAT_018a)[param_1] = DAT_0003 & 0x33 | DAT_0002;
      return;
    }
    if ((DAT_0006 == '\b') && ((DAT_000e & 0x10) != 0)) {
      DAT_018a = DAT_0002 & 0xf | DAT_018a & 0xf0;
      return;
    }
    (&DAT_018a)[param_1] = DAT_0002;
    return;
  }
  if ((DAT_000c & 0x10) == 0) {
    if ((DAT_0006 == '\b') && ((DAT_000e & 0x10) != 0)) {
      DAT_0002 = DAT_0002 & 3;
      DAT_018a = DAT_0003 & 0xc | DAT_0002 | DAT_018a & 0xf0;
      return;
    }
    DAT_0002 = DAT_0002 & 0x33;
    (&DAT_018a)[param_1] = DAT_0003 & 0xcc | DAT_0002;
    return;
  }
  if ((DAT_0006 == '\b') && ((DAT_000e & 0x10) != 0)) {
    DAT_018a = DAT_0002 & 0xf | DAT_018a & 0xf0;
    return;
  }
  (&DAT_018a)[param_1] = DAT_0002;
  return;
}

