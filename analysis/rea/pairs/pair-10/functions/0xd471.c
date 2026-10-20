
void FUN_d471(void)

{
  char cVar1;
  byte bVar2;
  bool bVar3;
  
  cVar1 = '\a';
  DAT_002c = 0;
  DAT_002a = 0;
  DAT_002b = '\0';
  do {
    bVar2 = DAT_0020._1_1_ & 1;
    DAT_0020._1_1_ = DAT_0020._1_1_ >> 1;
    if (bVar2 != 0) {
      bVar3 = CARRY1((byte)DAT_0020,DAT_002a);
      DAT_002a = (byte)DAT_0020 + DAT_002a;
      DAT_002b = DAT_002c + DAT_002b + bVar3;
    }
    bVar2 = (byte)DAT_0020 >> 7;
    DAT_0020._0_1_ = (byte)DAT_0020 << 1;
    DAT_002c = DAT_002c << 1 | bVar2;
    cVar1 = cVar1 + -1;
  } while (-1 < cVar1);
  return;
}

