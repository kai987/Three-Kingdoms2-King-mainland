
void FUN_a03f(byte param_1)

{
  bool bVar1;
  
  do {
    if (0x13 < param_1) break;
    DAT_6f94 = DAT_6f94 + 1;
    bVar1 = (char)((&DAT_6fa1)[param_1] + '\x01') < '\0';
    if ((((&DAT_6fa1)[param_1] != -1) && (FUN_a944(), !bVar1)) && ((&DAT_0664)[param_1] != -1)) {
      DAT_6f96 = DAT_6f96 + '\x01';
      DAT_6f8c = param_1;
      FUN_a099();
      if (DAT_6f8f != '\x03') {
        DAT_6f8b = 0xff;
        return;
      }
      DAT_6f95 = DAT_6f95 + '\x01';
    }
    param_1 = DAT_6f94;
  } while (DAT_6f94 < 0x14);
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

