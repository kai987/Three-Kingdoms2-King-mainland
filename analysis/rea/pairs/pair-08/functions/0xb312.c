
void FUN_b312(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xb3;
  FUN_f266(0x30);
  bVar2 = DAT_050e << 3;
  do {
    if (*(char *)(bVar2 + 0x9d72) < '\0') {
      cVar1 = '\0';
LAB_b334:
      DAT_0020 = cVar1 * '\"';
      uStack0000 = 0xb3;
      FUN_f266(0x26);
      bVar2 = *(byte *)((byte)(DAT_050e << 1) + 0x8000);
      bVar3 = CARRY1(bVar2,DAT_0020);
      DAT_0020 = bVar2 + DAT_0020;
      DAT_0021 = *(char *)((byte)(DAT_050e << 1) + 0x8001) + bVar3;
      bVar2 = 0;
      do {
        *(undefined1 *)(bVar2 + 0x22) = (&DAT_b36d)[bVar2];
        bVar2 = bVar2 + 1;
      } while (bVar2 < 4);
      return;
    }
    if (*(char *)(bVar2 + 0x9d72) == DAT_052a) {
      cVar1 = *(char *)(bVar2 + 0x9e62);
      goto LAB_b334;
    }
    bVar2 = bVar2 + 1;
  } while( true );
}

