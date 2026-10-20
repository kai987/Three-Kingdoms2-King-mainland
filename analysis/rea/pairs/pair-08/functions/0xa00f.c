
void thunk_FUN_cd78(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  undefined1 uStack0000;
  
  DAT_050a = 0;
  if (0x1e < DAT_0506) {
    DAT_0000 = 0;
    FUN_ceab();
    return;
  }
  uStack0000 = 0xcd;
  FUN_cd06(1);
  bVar5 = DAT_0524 - DAT_001a;
  bVar3 = (DAT_0525 - DAT_001b) -
          (((DAT_001a & (~DAT_0524 | bVar5) | bVar5 & ~DAT_0524) & 0x80) == 0);
  if ((((DAT_001b & (~DAT_0525 | bVar3) | bVar3 & ~DAT_0525) & 0x80) != 0) &&
     ((bVar5 != 0 || (bVar3 != 0)))) {
    bVar1 = DAT_0522 - DAT_001c;
    bVar4 = (DAT_0523 - DAT_001d) -
            (((DAT_001c & (~DAT_0522 | bVar1) | bVar1 & ~DAT_0522) & 0x80) == 0);
    DAT_0524 = bVar5;
    DAT_0525 = bVar3;
    if ((((DAT_001d & (~DAT_0523 | bVar4) | bVar4 & ~DAT_0523) & 0x80) != 0) &&
       ((bVar1 != 0 || (bVar4 != 0)))) {
      DAT_0010 = 0xf;
      DAT_0011 = 1;
      uStack0000 = 0xcd;
      DAT_0522 = bVar1;
      DAT_0523 = bVar4;
      FUN_ce40();
      uStack0000 = 0xcd;
      FUN_cf60();
      if (DAT_052e != '\0') {
        DAT_0010 = 0xf0;
        DAT_0011 = 0x10;
        DAT_000b = 0;
        DAT_000c = 0;
        uStack0000 = 0xce;
        FUN_ce40();
        DAT_000a = 0x6d;
        uStack0000 = 0xce;
        far_call_inline_word(0x2e);
        DAT_00a0 = DAT_00a0 << 1;
      }
      bVar5 = 0;
      while( true ) {
        if ((*(char *)(bVar5 + 0x4db) != -1) &&
           (cVar2 = *(char *)(bVar5 + 0x4db) + -1, *(char *)(bVar5 + 0x4db) = cVar2, cVar2 == '\0'))
        {
          (&DAT_04d8)[bVar5] = 0xff;
        }
        if (bVar5 == 4) break;
        bVar5 = 4;
      }
      return;
    }
    DAT_0522 = 0;
    DAT_0523 = 0;
    FUN_cf06();
    return;
  }
  DAT_0524 = 0;
  DAT_0525 = 0;
  DAT_0000 = 0x80;
  FUN_ceab();
  return;
}

