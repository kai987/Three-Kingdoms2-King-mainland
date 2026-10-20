
void FUN_c885(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 8;
  do {
    (&DAT_6f7b)[bVar1] = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  DAT_0028 = DAT_0037 << 3;
  do {
    do {
      uStack0000 = 200;
      bVar1 = FUN_d4ad(8);
    } while ((&DAT_6f7b)[bVar1] == '\0');
    (&DAT_6f7b)[bVar1] = 0;
    if (-1 < *(char *)((byte)(bVar1 + DAT_0028) + 0x9d72)) {
      uStack0000 = 200;
      FUN_c8c3();
    }
    bVar1 = 0;
    while ((&DAT_6f7b)[bVar1] != -1) {
      bVar1 = bVar1 + 1;
      if (7 < bVar1) {
        return;
      }
    }
  } while( true );
}

