
void FUN_f387(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf3;
  bVar1 = FUN_f25f(0x31);
  DAT_0000 = bVar1 * '\f';
  DAT_0001 = (((CARRY1(bVar1 * '\x02',bVar1) - ((char)bVar1 >> 7)) * '\x02' |
              (byte)(bVar1 * '\x03') >> 7) << 1 | (bVar1 * '\x03' & 0x7f) >> 6) + 0x80;
  return;
}

