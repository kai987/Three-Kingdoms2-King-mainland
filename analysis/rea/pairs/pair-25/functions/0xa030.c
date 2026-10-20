
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_bb73(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xbb;
  region_address(DAT_0402);
  bVar3 = 2;
  if (DAT_042d != -0x10) {
    bVar3 = 4;
  }
  DAT_0002 = *(byte *)(_DAT_0000 + (ushort)bVar3) - DAT_042f;
  bVar1 = ~*(byte *)(_DAT_0000 + (ushort)bVar3);
  bVar2 = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1));
  bVar1 = (bVar2 - DAT_0430) - (((DAT_042f & (bVar1 | DAT_0002) | DAT_0002 & bVar1) & 0x80) == 0);
  bVar2 = ~bVar2;
  if (((DAT_0430 & (bVar2 | bVar1) | bVar1 & bVar2) & 0x80) == 0) {
    DAT_042e = DAT_042d;
    DAT_042d = 0;
    return;
  }
  *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) = bVar1;
  *(byte *)(_DAT_0000 + (ushort)bVar3) = DAT_0002;
  DAT_000a = DAT_042c;
  uStack0000 = 0xbb;
  FUN_a1eb();
  bVar3 = 2;
  if (DAT_042d != -0x10) {
    bVar3 = 4;
  }
  bVar4 = CARRY1(*(byte *)(_DAT_0000 + (ushort)bVar3),DAT_042f);
  *(byte *)(_DAT_0000 + (ushort)bVar3) = *(byte *)(_DAT_0000 + (ushort)bVar3) + DAT_042f;
  *(byte *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) =
       *(char *)(_DAT_0000 + (ushort)(byte)(bVar3 + 1)) + DAT_0430 + bVar4;
  DAT_0010._0_1_ = DAT_0000;
  DAT_0010._1_1_ = DAT_0001;
  uStack0000 = 0xbb;
  FUN_a52a(bVar3);
  return;
}

