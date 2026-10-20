
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_edf5(char param_1)

{
  DAT_000a = *(undefined1 *)(_DAT_0010 + (ushort)(byte)(param_1 * '\x02'));
  DAT_000c = *(undefined1 *)(_DAT_0010 + (ushort)(byte)(param_1 * '\x02' + 1));
  DAT_0002 = 0;
  FUN_f1ad();
  return;
}

