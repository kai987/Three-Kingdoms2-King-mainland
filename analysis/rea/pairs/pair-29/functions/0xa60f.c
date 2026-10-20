
void FUN_a60f(void)

{
  byte bVar1;
  
  bVar1 = 0x28;
  do {
    (&DAT_031c)[bVar1] = 1;
    (&DAT_034c)[bVar1] = 1;
    bVar1 = bVar1 - 1;
  } while (bVar1 != 0);
  return;
}

