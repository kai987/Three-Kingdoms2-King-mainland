
void FUN_b2ae(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  byte bStack0000;
  
  bStack0000 = 0xb2;
  FUN_f266(0x30);
  bStack0000 = DAT_050e << 3;
  do {
    if (*(char *)(bStack0000 + 0x9d72) < '\0') {
      cVar1 = '\0';
LAB_b2d9:
      DAT_0020 = cVar1 << 5;
      bStack0000 = 0xb2;
      FUN_f266(0x26);
      bVar2 = *(byte *)((byte)(DAT_050e << 1) + 0x8c52);
      bVar3 = CARRY1(bVar2,DAT_0020);
      DAT_0020 = bVar2 + DAT_0020;
      DAT_0021 = *(char *)((byte)(DAT_050e << 1) + 0x8c53) + bVar3;
      bVar2 = 0;
      do {
        *(undefined1 *)(bVar2 + 0x22) = (&DAT_b30e)[bVar2];
        bVar2 = bVar2 + 1;
      } while (bVar2 < 4);
      return;
    }
    if (*(char *)(bStack0000 + 0x9d72) == DAT_052a) {
      FUN_f266(0x31);
      cVar1 = *(char *)(bStack0000 + 0x9ab4);
      goto LAB_b2d9;
    }
    bStack0000 = bStack0000 + 1;
  } while( true );
}

