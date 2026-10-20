
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ca87(void)

{
  undefined1 uStack0000;
  
  _DAT_0024 = CONCAT11((&DAT_cad9)[(byte)(DAT_0040 << 1)],(&DAT_cad8)[(byte)(DAT_0040 << 1)]);
  for (DAT_0026 = 0; *(char *)(_DAT_0024 + (ushort)DAT_0026) != -1; DAT_0026 = DAT_0026 + 1) {
    uStack0000 = 0xca;
    DAT_0027 = *(char *)(_DAT_0024 + (ushort)DAT_0026);
    FUN_caad();
  }
  return;
}

