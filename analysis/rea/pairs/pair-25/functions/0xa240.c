
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a240(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xa2;
  FUN_f25f(0x31);
  bVar2 = 0;
  bVar1 = 0;
  do {
    (&DAT_042c)[bVar1] = *(undefined1 *)(bVar2 + 0x6f07);
    bVar1 = bVar1 + 1;
    bVar2 = bVar1 * '\b';
  } while (bVar1 < 7);
  (&DAT_042c)[DAT_6f03] = 0xff;
  DAT_0010._0_1_ = 0;
  DAT_0010._1_1_ = '\0';
  do {
    bVar2 = 0;
    do {
      if ((&DAT_042c)[bVar2] == (byte)DAT_0010) goto LAB_a28b;
      bVar2 = bVar2 + 1;
    } while (bVar2 < 7);
    uStack0000 = 0xa2;
    officer_address((byte)DAT_0010);
    if ((*(byte *)(_DAT_0000 + 0xb) & 3) != 3) {
      DAT_0010._1_1_ = DAT_0010._1_1_ + '\x01';
    }
LAB_a28b:
    DAT_0010._0_1_ = (byte)DAT_0010 + 1;
    if (0xec < (byte)DAT_0010) {
      return;
    }
  } while( true );
}

