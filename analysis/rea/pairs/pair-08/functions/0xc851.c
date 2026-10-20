
void FUN_c851(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  
  bVar5 = DAT_0012 * '\x04' + DAT_0000 * '\x10';
  bVar4 = 0;
  do {
    cVar1 = (&DAT_c8de)[bVar5];
    *(char *)(bVar4 + 0x44c) = cVar1;
    bVar2 = cVar1 * '\x02';
    bVar3 = bVar4 * '\x03';
    DAT_0000 = bVar2;
    DAT_0001 = bVar4;
    (&DAT_042c)[bVar3] = (&DAT_c89e)[bVar2];
    (&DAT_042d)[bVar3] = (&DAT_c89e)[(byte)(bVar2 + 1)];
    (&DAT_042e)[bVar3] = 0;
    bVar5 = bVar5 + 1;
    bVar4 = DAT_0001 + 1;
  } while (bVar4 < 4);
  return;
}

