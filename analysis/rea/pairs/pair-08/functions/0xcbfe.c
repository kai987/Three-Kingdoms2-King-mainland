
void FUN_cbfe(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  bVar3 = false;
  bVar1 = 0;
  do {
    uStack0000 = 0xcc;
    FUN_cc92();
    if (((!bVar3) && ((&DAT_6fa1)[bVar1] != 0)) && ((byte)(&DAT_6fa1)[bVar1] < 5)) {
      (&DAT_6fa1)[bVar1] = 1;
    }
    bVar2 = bVar1 + 1;
    bVar3 = (char)(bVar1 - 0x13) < '\0';
    bVar1 = bVar2;
  } while (bVar2 < 0x14);
  return;
}

