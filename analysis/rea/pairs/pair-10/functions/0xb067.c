
byte FUN_b067(void)

{
  ushort uVar1;
  byte bVar2;
  byte bVar3;
  char cVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  uStack0000 = 0xb0;
  FUN_d2ab(DAT_002a,0);
  DAT_002b = DAT_002b >> 1 | DAT_002c << 7;
  bVar5 = CARRY1(*(byte *)(DAT_0022 + 6),DAT_002b);
  DAT_002d = *(byte *)(DAT_0022 + 6) + DAT_002b;
  DAT_002c = DAT_002c >> 1;
  *(byte *)(DAT_0022 + 6) = DAT_002d;
  DAT_002e = *(char *)(DAT_0022 + 7) + DAT_002c + bVar5;
  *(byte *)(DAT_0022 + 7) = DAT_002e;
  bVar2 = (*(byte *)(DAT_0022 + 7) + 0x3d) -
          ((*(byte *)(DAT_0022 + 6) + 0xb1 & ~*(byte *)(DAT_0022 + 6) & 0x80) == 0);
  bVar3 = ~*(byte *)(DAT_0022 + 7);
  if (((bVar3 & 0xc3 | bVar2 & 0xc3 | bVar2 & bVar3) & 0x80) != 0) {
    *(undefined1 *)(DAT_0022 + 6) = 0x4f;
    *(undefined1 *)(DAT_0022 + 7) = 0xc3;
  }
  bVar3 = (*(byte *)(DAT_0022 + 0xb) & 0xf0) >> 3;
  if ((bVar3 < 0xe) &&
     (bVar2 = DAT_002d - (&DAT_b0bc)[bVar3], uVar1 = (ushort)bVar3,
     bVar3 = (DAT_002e - (&DAT_b0bd)[uVar1]) -
             ((((&DAT_b0bc)[bVar3] & (~DAT_002d | bVar2) | bVar2 & ~DAT_002d) & 0x80) == 0),
     (((&DAT_b0bd)[uVar1] & (~DAT_002e | bVar3) | bVar3 & ~DAT_002e) & 0x80) != 0)) {
    DAT_002f = ((*(byte *)(DAT_0022 + 0xb) >> 4) + 1) * '\x10';
    bVar3 = *(byte *)(DAT_0022 + 0xb) & 0xf0;
    if (bVar3 < DAT_002f) {
      *(byte *)(DAT_0022 + 0xb) = *(byte *)(DAT_0022 + 0xb) & 0xf | DAT_002f;
      bVar3 = *(byte *)(DAT_0022 + 1);
      cVar4 = '\x06';
      if ((((bVar3 < 0x33) || (cVar4 = '\x05', bVar3 < 0x47)) || (cVar4 = '\x04', bVar3 < 0x51)) ||
         (cVar4 = '\x02', bVar3 < 0x5a)) {
        bVar3 = cVar4 + *(char *)(DAT_0022 + 1);
        *(byte *)(DAT_0022 + 1) = bVar3;
      }
      return bVar3;
    }
  }
  return bVar3;
}

