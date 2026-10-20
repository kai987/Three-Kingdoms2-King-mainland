
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_b6ef(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  bVar2 = 0xf < DAT_0020;
  if (0xf < DAT_0021) {
    bVar2 = bVar2 | 2;
  }
  bVar1 = *(byte *)(DAT_00a8 + (ushort)bVar2) << 1;
  _DAT_0022 = CONCAT11((&DAT_b7cc)[bVar1],(&DAT_b7cb)[bVar1]);
  uStack0000 = 0xb7;
  FUN_f266((&DAT_b8bb)[*(byte *)(DAT_00a8 + (ushort)bVar2)]);
  RAM0x0024 = &DAT_b74b;
  DAT_0026 = DAT_0020 & 0xf;
  bVar2 = *(byte *)(_DAT_0022 + (ushort)(byte)(DAT_0021 << 4 | DAT_0020 & 0xf));
  if (0x7f < bVar2) {
    return 0;
  }
  return (&DAT_b74b)[bVar2];
}

