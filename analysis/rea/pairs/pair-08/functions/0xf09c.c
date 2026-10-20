
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte FUN_f09c(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  bool bVar5;
  char cVar6;
  
  bVar2 = DAT_000a;
  if (((DAT_0002 & 0x80) == 0x80) && (bVar2 = DAT_000a - 8, 0xef < (byte)(DAT_000a - 8))) {
    DAT_000b = DAT_000b + -1;
    bVar2 = DAT_000a - 0x18;
  }
  DAT_000a = bVar2;
  if (((DAT_0002 & 0x40) == 0x40) &&
     (bVar1 = DAT_000c - 0x10, bVar2 = ~DAT_000c, DAT_000c = bVar1, (bVar1 & bVar2 & 0x80) == 0)) {
    DAT_000d = DAT_000d + -1;
  }
  bVar2 = DAT_000a - DAT_0090;
  bVar5 = ((DAT_0090 & (~DAT_000a | bVar2) | bVar2 & ~DAT_000a) & 0x80) == 0;
  if (bVar5) {
    bVar2 = bVar2 - 0x10;
  }
  DAT_000b = (DAT_000b - DAT_0091) - bVar5;
  bVar1 = DAT_000c - DAT_008e;
  bVar3 = (DAT_000d - DAT_008f) -
          (((DAT_008e & (~DAT_000c | bVar1) | bVar1 & ~DAT_000c) & 0x80) == 0);
  bVar4 = 0;
  DAT_000a = bVar2;
  DAT_000c = bVar1;
  DAT_000d = bVar3;
  while( true ) {
    if (DAT_007c == 0xff) {
      return bVar3;
    }
    DAT_000f = DAT_000b;
    bVar2 = *(byte *)(_DAT_0000 + (ushort)bVar4);
    if (bVar2 == 0x80) break;
    if ((DAT_0002 & 0x80) == 0x80) {
      bVar2 = 8 - *(char *)(_DAT_0000 + (ushort)bVar4);
    }
    if (bVar2 < 0x80) {
      cVar6 = CARRY1(bVar2,DAT_000a);
      DAT_000e = bVar2 + DAT_000a;
    }
    else {
      bVar2 = (bVar2 ^ 0xff) + 1;
      DAT_000e = DAT_000a - bVar2;
      cVar6 = -(((bVar2 & (~DAT_000a | DAT_000e) | DAT_000e & ~DAT_000a) & 0x80) == 0);
    }
    bVar3 = DAT_000b + cVar6;
    if ((bVar3 == 0) && (bVar3 = DAT_000e - 1, bVar3 < DAT_0004)) {
      *(byte *)(DAT_007c + 0x200) = bVar3;
      *(char *)(DAT_007c + 0x201) = *(char *)(_DAT_0000 + (ushort)(byte)(bVar4 + 1)) + DAT_0003;
      *(byte *)(DAT_007c + 0x202) = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar4 + 2)) ^ DAT_0002;
      bVar2 = *(byte *)(_DAT_0000 + (ushort)(byte)(bVar4 + 3));
      if ((DAT_0002 & 0x40) == 0x40) {
        bVar2 = 8 - *(char *)(_DAT_0000 + (ushort)(byte)(bVar4 + 3));
      }
      if ((char)bVar2 < '\0') {
        DAT_000e = bVar2 ^ 0xff;
        bVar3 = DAT_000c - DAT_000e;
        bVar2 = ~DAT_000c;
        bVar1 = DAT_000e & (bVar2 | bVar3);
        *(byte *)(DAT_007c + 0x203) = bVar3;
        bVar3 = DAT_000d - (((bVar1 | bVar3 & bVar2) & 0x80) == 0);
      }
      else {
        bVar5 = CARRY1(bVar2,DAT_000c);
        *(byte *)(DAT_007c + 0x203) = bVar2 + DAT_000c;
        bVar3 = DAT_000d + bVar5;
      }
      if (bVar3 == 0) {
        bVar4 = bVar4 + 4;
        DAT_007c = DAT_007c + 4;
        if (DAT_007c == 0) {
          DAT_007c = 0xff;
        }
      }
      else {
        bVar4 = bVar4 + 4;
      }
    }
    else {
      bVar4 = bVar4 + 4;
    }
  }
  DAT_000f = DAT_000b;
  return 0x80;
}

