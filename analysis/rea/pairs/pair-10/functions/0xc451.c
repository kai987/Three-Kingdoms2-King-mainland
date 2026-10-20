
char FUN_c451(void)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xc4;
  DAT_002a = FUN_d2ab(10);
  bVar3 = DAT_002a & 0x1f;
  DAT_002b = '\0';
  if ((7 < bVar3) && (DAT_002b = '\x04', 0xf < bVar3)) {
    DAT_002b = '\b';
  }
  bVar1 = (&DAT_c4d0)[DAT_6f5e] * '\x10' + DAT_002b;
  bVar4 = bVar1;
  if (((((byte)(&DAT_c4ee)[bVar1] <= bVar3) &&
       (bVar4 = bVar1 + 1, (byte)(&DAT_c4ee)[bVar4] <= bVar3)) &&
      (bVar4 = bVar1 + 2, (byte)(&DAT_c4ee)[bVar4] <= bVar3)) &&
     (bVar4 = bVar1 + 3, (byte)(&DAT_c4ee)[bVar4] <= bVar3)) {
    cVar2 = (&DAT_c4d0)[DAT_6f5e] * '\x10';
    bVar3 = cVar2 + 0xc;
    bVar1 = DAT_002a >> 5;
    if ((((byte)(&DAT_c4ee)[bVar3] <= bVar1) &&
        (bVar3 = cVar2 + 0xd, (byte)(&DAT_c4ee)[bVar3] <= bVar1)) &&
       ((bVar3 = cVar2 + 0xe, (byte)(&DAT_c4ee)[bVar3] <= bVar1 &&
        (bVar3 = cVar2 + 0xf, (byte)(&DAT_c4ee)[bVar3] <= bVar1)))) {
      return -1;
    }
    return (&DAT_c4ee)[bVar3] << 5;
  }
  return (&DAT_c4ee)[bVar4];
}

