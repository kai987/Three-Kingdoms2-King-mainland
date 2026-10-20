
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cc19(byte param_1)

{
  char cVar1;
  byte bStack0000;
  
  cVar1 = (&DAT_0664)[param_1];
  if (cVar1 != -1) {
    DAT_0011 = cVar1;
    bStack0000 = param_1;
    FUN_f387(cVar1);
    _DAT_0000 = (byte *)(ushort)*_DAT_0000;
    DAT_0002 = 0;
    DAT_0003 = 6;
    FUN_ebe9();
    _DAT_0000 = (byte *)CONCAT11(DAT_0006,DAT_0000);
    DAT_0002 = DAT_0007;
    DAT_0003 = 10;
    DAT_0004 = 0;
    FUN_ea7c();
    DAT_0012 = DAT_0001;
    officer_address(DAT_0011);
    DAT_0011 = *_DAT_0000;
    if (DAT_0011 < DAT_0012) {
      (&DAT_6fa1)[bStack0000] = (&DAT_6fa1)[bStack0000] << 4 | 6;
      DAT_0010 = DAT_0010 + '\x01';
    }
    return;
  }
  return;
}

