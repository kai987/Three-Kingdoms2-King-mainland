
void FUN_cbdf(void)

{
  byte bVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  bVar3 = false;
  bVar1 = 0;
  while( true ) {
    uStack0000 = 0xcb;
    FUN_cc92();
    if ((!bVar3) && ((&DAT_6fa1)[bVar1] == DAT_0000)) break;
    bVar2 = bVar1 + 1;
    bVar3 = (char)(bVar1 - 0x13) < '\0';
    bVar1 = bVar2;
    if (0x13 < bVar2) {
      return;
    }
  }
  DAT_0000 = DAT_0000 + -1;
  (&DAT_6fa1)[bVar1] = DAT_0000;
  return;
}

