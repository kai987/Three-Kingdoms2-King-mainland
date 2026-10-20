
void FUN_a9cc(void)

{
  byte bVar1;
  byte bVar2;
  byte bStack0000;
  
  bVar2 = 0;
  DAT_003c = 0;
  do {
    if (*(char *)(bVar2 + 0x664) != -1) {
      DAT_003c = DAT_003c + 1;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 10);
  bVar2 = 0;
  DAT_003d = 0;
  do {
    if (*(char *)(bVar2 + 0x66e) != -1) {
      DAT_003d = DAT_003d + 1;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 10);
  bVar2 = DAT_6f77;
  if (4 < DAT_003c) {
    bStack0000 = DAT_003c >> 2;
    bVar1 = bStack0000;
    for (; DAT_6f77 = bVar1, bStack0000 != 0; bStack0000 = bStack0000 - 1) {
      FUN_aa2d(0);
      bVar1 = DAT_6f77;
      bVar2 = DAT_6f77;
    }
  }
  DAT_6f77 = bVar2;
  bVar2 = DAT_6f78;
  if (4 < DAT_003d) {
    bStack0000 = DAT_003d >> 2;
    bVar1 = bStack0000;
    for (; DAT_6f78 = bVar1, bStack0000 != 0; bStack0000 = bStack0000 - 1) {
      FUN_aa2d(10);
      bVar1 = DAT_6f78;
      bVar2 = DAT_6f78;
    }
  }
  DAT_6f78 = bVar2;
  return;
}

