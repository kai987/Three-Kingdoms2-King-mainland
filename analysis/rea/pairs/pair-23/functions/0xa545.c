
void FUN_a545(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xa5;
  bVar1 = FUN_a8fd();
  DAT_0008 = (undefined1 *)
             CONCAT11(((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) + DAT_0003 +
                      CARRY1(bVar1 * '\x04',DAT_0002),bVar1 * '\x04' + DAT_0002);
  if ((DAT_000c & 8) == 0) {
    if ((DAT_0006 != '\0') || ((DAT_000e & 8) == 0)) {
      (&DAT_0142)[param_1] = *DAT_0008;
      param_1 = param_1 + 1;
    }
    (&DAT_0142)[param_1] = DAT_0008[2];
    return;
  }
  if ((DAT_0006 != '\0') || ((DAT_000e & 8) == 0)) {
    (&DAT_0142)[param_1] = DAT_0008[1];
    param_1 = param_1 + 1;
  }
  (&DAT_0142)[param_1] = DAT_0008[3];
  return;
}

