
void thunk_FUN_d57b(void)

{
  byte bVar1;
  byte bVar2;
  
  if (0xb < DAT_0500) {
    return;
  }
  DAT_0000 = 0;
  bVar2 = DAT_0508;
  if ((char)DAT_0508 < '\0') {
    bVar1 = DAT_008e + 2;
    if ((0xfd < DAT_008e) ||
       (DAT_009c = DAT_009c & 0xbf | 0x80, DAT_008e = bVar1, bVar2 = DAT_0508 | 0x80,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0x7f;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 1) < '\0') {
    bVar1 = DAT_008e - 2;
    if (((bVar1 & ~DAT_008e & 0x80) == 0) ||
       (DAT_009c = DAT_009c & 0x7f | 0x40, DAT_008e = bVar1, bVar2 = DAT_0508 | 0x40,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xbf;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 2) < '\0') {
    bVar1 = DAT_0090 - 2;
    if (((bVar1 & ~DAT_0090 & 0x80) == 0) ||
       (DAT_009c = DAT_009c & 0xdf | 0x10, DAT_0090 = bVar1, bVar2 = DAT_0508 | 0x20,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xdf;
    }
  }
  DAT_0508 = bVar2;
  bVar2 = DAT_0508;
  if ((char)(DAT_0508 << 3) < '\0') {
    bVar1 = DAT_0090 + 2;
    if ((0x8f < bVar1) ||
       (DAT_009c = DAT_009c & 0xef | 0x20, DAT_0090 = bVar1, bVar2 = DAT_0508 | 0x10,
       (bVar1 & 0xe) == 0)) {
      bVar2 = DAT_0508 & 0xef;
    }
  }
  DAT_0508 = bVar2;
  return;
}

