
/* WARNING: Control flow encountered bad instruction data */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a099(byte param_1)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  bool bVar4;
  char in_C;
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_b517((&DAT_6fa1)[param_1] & 0xf);
  bVar2 = *(byte *)(_DAT_00a0 + (ushort)param_1) | DAT_00a1;
  bVar1 = DAT_00a1 >> 1 | in_C << 7;
  _DAT_00a0 = CONCAT11(bVar1,DAT_00a0);
  bVar4 = bVar1 == 0;
  bVar3 = false;
  if ((byte)(in_C << 7) != 0) {
                    /* WARNING: Bad instruction - Truncating control flow here */
    halt_baddata();
  }
  while( true ) {
    if (!bVar4) {
      uStack0000 = 0xa0;
      FUN_a944(bVar2);
      if ((!bVar3) && ((&DAT_0664)[param_1] != -1)) {
        DAT_6f96 = DAT_6f96 + '\x01';
        uStack0000 = 0xa0;
        DAT_6f8c = param_1;
        FUN_a099();
        if (DAT_6f8f != '\x03') {
          DAT_6f8b = 0xff;
          return;
        }
        DAT_6f95 = DAT_6f95 + '\x01';
      }
    }
    if ((0x13 < DAT_6f94) || (0x13 < DAT_6f94)) break;
    bVar2 = (&DAT_6fa1)[DAT_6f94];
    bVar4 = bVar2 == 0xff;
    bVar3 = (char)(bVar2 + 1) < '\0';
    param_1 = DAT_6f94;
    DAT_6f94 = DAT_6f94 + 1;
  }
  if (DAT_6f96 == DAT_6f95) {
    DAT_6f94 = 0;
    DAT_6f8f = 3;
    DAT_6f8b = 0xff;
    return;
  }
  DAT_6f94 = 0;
  DAT_6f95 = 0;
  DAT_6f96 = 0;
  FUN_a03c();
  return;
}

