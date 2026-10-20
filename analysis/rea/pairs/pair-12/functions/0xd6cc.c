
void thunk_FUN_d6d0(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  DAT_0010 = *(byte *)(DAT_0509 + 0x600);
  DAT_0011 = *(byte *)(DAT_0509 + 0x614);
  DAT_0000 = DAT_0090 >> 4;
  if ((byte)(DAT_0011 - DAT_0000) < 0xf) {
    if (DAT_008e < 0xfc) {
      DAT_0000 = (byte)(DAT_008e + 4) >> 4;
    }
    else {
      DAT_0000 = 0x10;
    }
    if ((byte)(DAT_0010 - DAT_0000) < 0x10) {
      bVar1 = 0xf < DAT_0010;
      if (0xf < DAT_0011) {
        bVar1 = bVar1 | 2;
      }
      DAT_0000 = *(undefined1 *)(DAT_00a8 + (ushort)bVar1);
      uStack0000 = *(undefined1 *)(DAT_00a8 + (ushort)(bVar1 ^ 1));
                    /* WARNING: Subroutine does not return */
      far_call_inline_word(0x37);
    }
  }
  return;
}

