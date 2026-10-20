
void FUN_ac67(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xac;
  FUN_aebf();
  bVar2 = DAT_0522 - DAT_002a;
  bVar3 = (DAT_0523 - DAT_002b) -
          (((DAT_002a & (~DAT_0522 | bVar2) | bVar2 & ~DAT_0522) & 0x80) == 0);
  bVar1 = ~DAT_0523;
  DAT_0522 = bVar2;
  DAT_0523 = bVar3;
  if (((DAT_002b & (bVar1 | bVar3) | bVar3 & bVar1) & 0x80) == 0) {
    DAT_0522 = 0;
    DAT_0523 = 0;
  }
  bVar2 = DAT_0524 - DAT_002c;
  bVar3 = (DAT_0525 - DAT_002d) -
          (((DAT_002c & (~DAT_0524 | bVar2) | bVar2 & ~DAT_0524) & 0x80) == 0);
  bVar1 = ~DAT_0525;
  DAT_0524 = bVar2;
  DAT_0525 = bVar3;
  if (((DAT_002d & (bVar1 | bVar3) | bVar3 & bVar1) & 0x80) == 0) {
    DAT_0524 = 0;
    DAT_0525 = 0;
  }
  uStack0000 = 0xac;
  FUN_ce67();
  uStack0000 = 0xac;
  FUN_cedd();
  uStack0000 = 0xac;
  FUN_d105(DAT_0038);
  bVar4 = CARRY1(DAT_0522,DAT_0524);
  *(byte *)(DAT_0020 + 4) = DAT_0522 + DAT_0524;
  *(byte *)(DAT_0020 + 5) = DAT_0523 + DAT_0525 + bVar4;
  bVar4 = CARRY1(DAT_0526,DAT_0528);
  *(byte *)(DAT_0020 + 2) = DAT_0526 + DAT_0528;
  *(char *)(DAT_0020 + 3) = DAT_0527 + DAT_0529 + bVar4;
  return;
}

