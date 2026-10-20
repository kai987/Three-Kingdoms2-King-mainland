
void FUN_c75b(char param_1)

{
  byte bVar1;
  
  bVar1 = 0x13;
  do {
    if (param_1 == *(char *)(bVar1 + 0x664)) {
      return;
    }
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  return;
}

