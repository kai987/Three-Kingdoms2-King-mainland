
void FUN_a03c(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  
  do {
    if (0x13 < DAT_6f94) break;
    bVar3 = (char)((&DAT_6fa1)[DAT_6f94] + '\x01') < '\0';
    bVar1 = DAT_6f94 + 1;
    if ((((&DAT_6fa1)[DAT_6f94] != -1) &&
        (bVar2 = DAT_6f94, DAT_6f94 = DAT_6f94 + 1, FUN_a944(), bVar1 = DAT_6f94, !bVar3)) &&
       ((&DAT_0664)[bVar2] != -1)) {
      DAT_6f96 = DAT_6f96 + '\x01';
      DAT_6f8c = bVar2;
      FUN_a099();
      if (DAT_6f8f != '\x03') {
        DAT_6f8b = 0xff;
        return;
      }
      DAT_6f95 = DAT_6f95 + '\x01';
      bVar1 = DAT_6f94;
    }
    DAT_6f94 = bVar1;
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

