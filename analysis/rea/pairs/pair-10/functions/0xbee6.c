
void FUN_bee6(void)

{
  byte bVar1;
  byte bVar2;
  
  do {
    bVar1 = DAT_6f03;
    (&DAT_6f83)[DAT_6f03] = (&DAT_6f83)[DAT_6f03] + '\x01';
    bVar2 = (&DAT_6f83)[bVar1];
    if (0x1d < bVar2) {
      DAT_6f62 = DAT_6f62 + '\x01';
      if (DAT_6f62 == '\x03') {
        DAT_6f62 = 0;
        FUN_d140();
        return;
      }
      bVar2 = 0;
    }
    (&DAT_6f83)[bVar1] = bVar2;
    DAT_6f5e = bVar2;
    bVar2 = FUN_d105();
  } while (bVar2 != DAT_6f03);
  return;
}

