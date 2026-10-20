
void FUN_c86a(byte param_1)

{
  byte bVar1;
  byte bStack0000;
  
  bStack0000 = param_1;
  FUN_f266(0x30);
  bVar1 = bStack0000;
  if ((*(byte *)(bStack0000 + 0x8ffc) & 8) != 0) {
    bStack0000 = 200;
    bVar1 = FUN_d304(bVar1);
    if (bVar1 < 10) {
      return;
    }
  }
  return;
}

