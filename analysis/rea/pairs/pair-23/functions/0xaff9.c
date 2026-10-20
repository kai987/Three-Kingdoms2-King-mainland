
void FUN_aff9(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xaf;
  FUN_b08f();
  bVar1 = 0x7f;
  do {
    *(undefined1 *)(bVar1 + 0x680) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  cVar2 = '\x13';
  do {
    uStack0000 = 0xb0;
    FUN_b00f();
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  return;
}

