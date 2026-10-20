
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_dbb1(void)

{
  byte bVar1;
  
  _DAT_000a = CONCAT11((&DAT_dbd0)[(byte)(DAT_0000 << 1)],(&DAT_dbcf)[(byte)(DAT_0000 << 1)]);
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x100) = *(undefined1 *)(_DAT_000a + (ushort)bVar1);
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  return;
}

