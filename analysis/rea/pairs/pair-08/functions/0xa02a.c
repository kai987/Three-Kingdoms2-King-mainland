
void thunk_FUN_d6cd(void)

{
  byte bVar1;
  
  bVar1 = DAT_0000;
  *(undefined1 *)(DAT_0000 + 0x600) = 0xff;
  *(undefined1 *)(bVar1 + 0x614) = 0xff;
  *(undefined1 *)(bVar1 + 0x628) = 0xff;
  *(undefined1 *)(bVar1 + 0x63c) = 0xff;
  *(undefined1 *)(bVar1 + 0x650) = 0xff;
  (&DAT_0664)[bVar1] = 0xff;
  (&DAT_6fa1)[bVar1] = 0xff;
  bVar1 = 0;
  if ((DAT_04d8 != DAT_0000) && (bVar1 = 4, DAT_04dc != DAT_0000)) {
    return;
  }
  DAT_0001 = bVar1 + 4;
  do {
    (&DAT_04d8)[bVar1] = 0xff;
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0001);
  return;
}

