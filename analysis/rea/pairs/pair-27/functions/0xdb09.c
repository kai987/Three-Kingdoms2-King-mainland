
void FUN_db09(void)

{
  DAT_0001 = 0;
  if (DAT_048b == '\0') {
    DAT_0000 = 1;
  }
  else if (DAT_048b == '\x01') {
    DAT_0000 = 10;
  }
  else if (DAT_048b == '\x02') {
    DAT_0000 = 100;
  }
  else {
    DAT_0001 = 3;
    DAT_0000 = 0xe8;
  }
  return;
}

