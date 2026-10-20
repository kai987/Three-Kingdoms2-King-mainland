
void FUN_cb6a(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    DAT_001a = (&DAT_cb96)[bVar1];
    bVar4 = false;
    bVar2 = 0;
    do {
      uStack0000 = 0xcb;
      FUN_a944();
      if ((!bVar4) && ((&DAT_6fa1)[bVar2] == DAT_001a)) {
        (&DAT_6fa1)[bVar2] = (&DAT_6fa1)[bVar2] << 4 | 5;
        return;
      }
      bVar3 = bVar2 + 1;
      bVar4 = (char)(bVar2 - 0x13) < '\0';
      bVar2 = bVar3;
    } while (bVar3 < 0x14);
    bVar1 = bVar1 + 1;
    if (3 < bVar1) {
      return;
    }
  } while( true );
}

