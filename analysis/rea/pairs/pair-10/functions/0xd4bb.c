
void FUN_d4bb(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0056 = param_1;
  if (param_1 < 0xf) {
    do {
      uStack0000 = 0xd4;
      bVar1 = FUN_e88a();
    } while (DAT_0056 <= (bVar1 & 0xf));
    return;
  }
  do {
    uStack0000 = 0xd4;
    bVar1 = FUN_e88a();
  } while (DAT_0056 <= bVar1);
  return;
}

