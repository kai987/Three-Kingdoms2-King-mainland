
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d7fb(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xd8;
  officer_address(DAT_000a);
  DAT_000b = DAT_000b >> 1 | DAT_000c << 7;
  bVar4 = CARRY1(*(byte *)(_DAT_0000 + 6),DAT_000b);
  DAT_000d = *(byte *)(_DAT_0000 + 6) + DAT_000b;
  DAT_000c = DAT_000c >> 1;
  *(byte *)(_DAT_0000 + 6) = DAT_000d;
  DAT_000e = *(char *)(_DAT_0000 + 7) + DAT_000c + bVar4;
  *(byte *)(_DAT_0000 + 7) = DAT_000e;
  bVar2 = (*(byte *)(_DAT_0000 + 7) + 0x3d) -
          ((*(byte *)(_DAT_0000 + 6) + 0xb1 & ~*(byte *)(_DAT_0000 + 6) & 0x80) == 0);
  bVar1 = ~*(byte *)(_DAT_0000 + 7);
  if (((bVar1 & 0xc3 | bVar2 & 0xc3 | bVar2 & bVar1) & 0x80) != 0) {
    *(undefined1 *)(_DAT_0000 + 6) = 0x4f;
    *(undefined1 *)(_DAT_0000 + 7) = 0xc3;
  }
  bVar1 = (*(byte *)(_DAT_0000 + 0xb) & 0xf0) >> 3;
  if (((bVar1 < 0xe) &&
      (bVar2 = DAT_000d - (&DAT_d85b)[bVar1],
      bVar2 = (DAT_000e - (&DAT_d85c)[bVar1]) -
              ((((&DAT_d85b)[bVar1] & (~DAT_000d | bVar2) | bVar2 & ~DAT_000d) & 0x80) == 0),
      (((&DAT_d85c)[bVar1] & (~DAT_000e | bVar2) | bVar2 & ~DAT_000e) & 0x80) != 0)) &&
     (DAT_000f = ((*(byte *)(_DAT_0000 + 0xb) >> 4) + 1) * '\x10',
     (*(byte *)(_DAT_0000 + 0xb) & 0xf0) < DAT_000f)) {
    *(byte *)(_DAT_0000 + 0xb) = *(byte *)(_DAT_0000 + 0xb) & 0xf | DAT_000f;
    bVar1 = *(byte *)(_DAT_0000 + 1);
    cVar3 = '\x06';
    if (((bVar1 < 0x33) || (cVar3 = '\x05', bVar1 < 0x47)) ||
       ((cVar3 = '\x04', bVar1 < 0x51 || (cVar3 = '\x02', bVar1 < 0x5a)))) {
      *(char *)(_DAT_0000 + 1) = cVar3 + *(char *)(_DAT_0000 + 1);
    }
    return;
  }
  DAT_000f = 0;
  return;
}

