
void thunk_FUN_a830(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa856);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xa8;
  FUN_a957(*(undefined1 *)(DAT_0509 + 0x664));
  uStack0000 = 0xa8;
  FUN_a976(*(undefined1 *)(DAT_0509 + 0x664));
  DAT_007e = DAT_007e | 4;
  return;
}

