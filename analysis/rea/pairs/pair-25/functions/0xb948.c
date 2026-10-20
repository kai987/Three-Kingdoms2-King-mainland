
byte FUN_b948(byte param_1)

{
  byte bVar1;
  
  bVar1 = (byte)DAT_0010 - (&DAT_0498)[param_1];
  bVar1 = (DAT_0010._1_1_ - (&DAT_0499)[param_1]) -
          ((((&DAT_0498)[param_1] & (~(byte)DAT_0010 | bVar1) | bVar1 & ~(byte)DAT_0010) & 0x80) ==
          0);
  if ((((&DAT_0499)[param_1] & (~DAT_0010._1_1_ | bVar1) | bVar1 & ~DAT_0010._1_1_) & 0x80) == 0) {
    (&DAT_0498)[param_1] = (byte)DAT_0010;
    bVar1 = DAT_0010._1_1_;
    (&DAT_0499)[param_1] = DAT_0010._1_1_;
  }
  return bVar1;
}

