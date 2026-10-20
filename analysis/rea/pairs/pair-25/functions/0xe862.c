
void FUN_e862(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0010._0_1_ = param_1;
  if (param_1 < 0xf) {
    do {
      uStack0000 = 0xe8;
      bVar1 = FUN_e87a();
    } while ((byte)DAT_0010 <= (bVar1 & 0xf));
    return;
  }
  do {
    uStack0000 = 0xe8;
    bVar1 = FUN_e87a();
  } while ((byte)DAT_0010 <= bVar1);
  return;
}

