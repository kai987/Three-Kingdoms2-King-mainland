
void FUN_a93f(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xa9;
  FUN_ab26();
  bVar1 = 0x3f;
  do {
    *(undefined1 *)(bVar1 + 0x680) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  bVar1 = 0x13;
  do {
    if (*(char *)(bVar1 + 0x600) == DAT_0018) {
      *(byte *)(*(byte *)(bVar1 + 0x614) + 0x680) = bVar1;
    }
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  return;
}

