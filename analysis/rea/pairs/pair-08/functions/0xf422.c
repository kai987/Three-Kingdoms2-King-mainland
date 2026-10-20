
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

char FUN_f422(byte param_1)

{
  char cVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf4;
  FUN_f458();
  do {
    do {
      if (*(char *)(_DAT_0002 + (ushort)param_1) != DAT_0000) {
        return *(char *)(_DAT_0002 + (ushort)param_1);
      }
      uStack0000 = 0xf4;
      FUN_f468();
      param_1 = param_1 + 1;
    } while (param_1 != 0);
    cVar1 = DAT_0003 + '\x01';
    _DAT_0002 = CONCAT11(cVar1,DAT_0002);
  } while (cVar1 != -0x80);
  return '\0';
}

