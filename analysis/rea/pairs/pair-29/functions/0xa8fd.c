
void FUN_a8fd(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0x3a;
  do {
    *(undefined1 *)(bVar1 + 0x380) = *(undefined1 *)(bVar1 + 0xa91d);
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 0xa9;
  FUN_a957(DAT_04ae);
  uStack0000 = 0xa9;
  FUN_a976(DAT_04ae);
  DAT_007e = DAT_007e | 4;
  return;
}

