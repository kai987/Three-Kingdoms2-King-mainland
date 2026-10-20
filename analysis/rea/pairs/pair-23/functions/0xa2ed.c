
void FUN_a2ed(void)

{
  byte bVar1;
  byte bVar2;
  
  bVar2 = (byte)DAT_000a - 0x10;
  bVar1 = ~(byte)DAT_000a;
  DAT_000a._0_1_ = bVar2;
  DAT_000a._1_1_ = DAT_000a._1_1_ - ((bVar2 & bVar1 & 0x80) == 0);
  return;
}

