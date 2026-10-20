
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_a9a8(undefined1 param_1)

{
  undefined1 *puVar1;
  short sVar2;
  undefined1 uStack0000;
  
  sVar2 = _DAT_0000;
  uStack0000 = DAT_0000;
  FUN_f368(param_1);
  puVar1 = (undefined1 *)(_DAT_0000 + 3);
  _DAT_0000 = CONCAT11((char)((ushort)sVar2 >> 8),uStack0000);
  return *puVar1;
}

