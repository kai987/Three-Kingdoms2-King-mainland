
void FUN_ae58(byte param_1)

{
  if ((DAT_009c & 0x10) == 0) {
    if ((DAT_0006 == '\b') && ((DAT_000c & 0x10) != 0)) {
      DAT_019e = DAT_0002 & 0x33 | DAT_019e & 0xcc;
      return;
    }
    (&DAT_019e)[param_1] = DAT_0002;
    return;
  }
  if ((DAT_0006 == '\b') && ((DAT_000c & 0x10) != 0)) {
    DAT_019e = DAT_0002 & 0x33 | DAT_019e & 0xcc;
    return;
  }
  (&DAT_019e)[param_1] = DAT_0002;
  return;
}

