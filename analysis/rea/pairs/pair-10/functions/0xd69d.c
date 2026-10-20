
byte FUN_d69d(void)

{
  byte bVar1;
  
  if (((*(byte *)(DAT_0020 + 3) - 0x27) -
       ((*(byte *)(DAT_0020 + 2) - 0x10 & ~*(byte *)(DAT_0020 + 2) & 0x80) == 0) &
       ~*(byte *)(DAT_0020 + 3) & 0x80) != 0) {
    *(undefined1 *)(DAT_0020 + 2) = 0xf;
    *(undefined1 *)(DAT_0020 + 3) = 0x27;
  }
  bVar1 = (*(byte *)(DAT_0020 + 5) - 0x27) -
          ((*(byte *)(DAT_0020 + 4) - 0x10 & ~*(byte *)(DAT_0020 + 4) & 0x80) == 0);
  if ((bVar1 & ~*(byte *)(DAT_0020 + 5) & 0x80) != 0) {
    *(undefined1 *)(DAT_0020 + 4) = 0xf;
    bVar1 = 0x27;
    *(undefined1 *)(DAT_0020 + 5) = 0x27;
  }
  return bVar1;
}

