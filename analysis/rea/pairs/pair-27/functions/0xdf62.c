
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_df62(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  _DAT_0000 = (byte *)CONCAT11(DAT_0001,(&DAT_dfee)[DAT_000f & 7]);
  if (((((&DAT_04e0)[DAT_000f >> 3] & (&DAT_dfee)[DAT_000f & 7]) == 0) || ((DAT_005e & 8) == 0)) &&
     (((&DAT_dfd0)[DAT_000f] & DAT_000e) == 0)) {
    uStack0000 = 0xdf;
    region_address(DAT_000f);
    bVar1 = *_DAT_0000;
    *(undefined *)(param_1 + 0x201) = (&DAT_dfc0)[bVar1 & 7];
    *(undefined *)(param_1 + 0x202) = (&DAT_dfc8)[bVar1 & 7];
    bVar1 = DAT_000f & 0x1f;
    *(undefined *)(param_1 + 0x203) = (&DAT_dee9)[bVar1];
    *(undefined *)(param_1 + 0x200) = (&DAT_df07)[bVar1];
    return;
  }
  return;
}

