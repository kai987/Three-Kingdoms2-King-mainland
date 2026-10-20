
void FUN_ce1f(byte param_1)

{
  byte bStack0000;
  
  if ((DAT_6fea & 4) != 0) {
    DAT_00a4 = 3;
  }
  if ((DAT_6fea & 8) != 0) {
    DAT_00a4 = 4;
  }
  bStack0000 = 0xce;
  FUN_f25f(0x21);
  if ((param_1 & 1) == 0) {
    DAT_0003 = 0;
    DAT_00b8 = (&DAT_ced6)[DAT_0000];
  }
  else {
    DAT_0003 = 0x40;
    DAT_00b9 = (&DAT_ced6)[DAT_0000];
  }
  DAT_0005 = 0;
  bStack0000 = ((DAT_00a4 & 7) + *(char *)(DAT_0000 + 0x99a0)) * '\x02';
  DAT_0000 = *(undefined1 *)(bStack0000 + 0x9aa0);
  DAT_0001 = *(undefined1 *)(bStack0000 + 0x9aa1);
  DAT_000c = DAT_04bc;
  if (DAT_04bc == '\0') {
    DAT_000c = '\x10';
  }
  DAT_0002 = 0;
  DAT_0004 = 0xa0;
  FUN_f1b7();
  DAT_04bc = 0;
  if ((((-1 < (char)DAT_00a4) && ((DAT_007e & 1) != 0)) && (DAT_0304 != -1)) &&
     ((DAT_0303 == '\0' && ((DAT_005e & 8) != 0)))) {
    DAT_0000 = *(undefined1 *)(bStack0000 + 0x9d64);
    DAT_0001 = *(undefined1 *)(bStack0000 + 0x9d65);
    FUN_f1b7();
    return;
  }
  DAT_0000 = *(undefined1 *)(bStack0000 + 0x9bac);
  DAT_0001 = *(undefined1 *)(bStack0000 + 0x9bad);
  FUN_f1b7();
  return;
}

