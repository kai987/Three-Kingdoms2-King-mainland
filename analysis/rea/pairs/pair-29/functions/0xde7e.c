
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_de7e(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xde;
  DAT_0000 = FUN_f25f(0x21);
  bVar2 = 0;
  bVar1 = DAT_0000 * '\x03';
  DAT_0001 = (((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) << 1 | (bVar1 & 0x3f) >> 5) << 1 |
             (bVar1 & 0x1f) >> 4;
  _DAT_0002 = CONCAT11(DAT_0001 + 0x94 + (0x93 < (byte)(DAT_0000 * '0')),DAT_0000 * '0' + 0x6c);
  do {
    *(undefined1 *)(bVar2 + 0xae) = *(undefined1 *)(_DAT_0002 + (ushort)bVar2);
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x30);
  return;
}

