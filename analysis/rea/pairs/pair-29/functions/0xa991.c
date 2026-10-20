
void FUN_a991(void)

{
  undefined1 uVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  if (DAT_0001 == '\0') {
    bVar2 = 0x3a;
    do {
      *(undefined1 *)(bVar2 + 0x380) = (&DAT_a9fd)[bVar2];
      bVar2 = bVar2 - 1;
    } while (-1 < (char)bVar2);
  }
  else {
    bVar2 = 0x3a;
    do {
      *(undefined1 *)(bVar2 + 0x380) = *(undefined1 *)(bVar2 + 0xa9c3);
      bVar2 = bVar2 - 1;
    } while (-1 < (char)bVar2);
  }
  uStack0000 = DAT_0000;
  FUN_a957();
  uVar1 = uStack0000;
  uStack0000 = 0xa9;
  FUN_a976(uVar1);
  DAT_007e = DAT_007e | 4;
  return;
}

