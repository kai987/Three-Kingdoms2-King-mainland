
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a61d(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0001 = DAT_0310 >> 7;
  DAT_0000 = DAT_0310 << 1;
  uStack0000 = 0xa6;
  bVar1 = FUN_a690();
  _DAT_0000 = (undefined1 *)
              CONCAT11(DAT_0001 + (&DAT_a673)[(byte)(bVar1 << 1)] +
                       CARRY1(DAT_0000,(&DAT_a672)[(byte)(bVar1 << 1)]),
                       DAT_0000 + (&DAT_a672)[(byte)(bVar1 << 1)]);
  if ((bVar1 < 9) && (2 < bVar1)) {
    DAT_00a6._0_1_ = *_DAT_0000;
    DAT_00a6._1_1_ = _DAT_0000[1] + '@';
    return;
  }
  DAT_00a6._0_1_ = *_DAT_0000;
  DAT_00a6._1_1_ = _DAT_0000[1] + ' ';
  return;
}

