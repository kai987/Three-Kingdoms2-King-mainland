
char FUN_dd53(char param_1)

{
  char cStack0000;
  
  DAT_0000 = *(undefined1 *)((byte)(param_1 * '\x02') + 0x970c);
  DAT_0001 = *(undefined1 *)((byte)(param_1 * '\x02' + 1) + 0x970c);
  DAT_000c = 0;
  DAT_000a = 0;
  DAT_0002 = 0;
  cStack0000 = param_1;
  FUN_f1ad();
  return cStack0000;
}

