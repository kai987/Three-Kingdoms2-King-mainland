
void thunk_FUN_a212(void)

{
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  DAT_000c = '\0';
  DAT_000d = 0;
  do {
    DAT_2007 = *DAT_000a;
    if ((char)((char)DAT_000a + '\x01') == '\0') {
      DAT_000a._1_1_ = DAT_000a._1_1_ + '\x01';
    }
    DAT_000a = (undefined1 *)CONCAT11(DAT_000a._1_1_,(char)DAT_000a + '\x01');
    DAT_000c = DAT_000c + '\x01';
    if (DAT_000c == '\0') {
      DAT_000d = DAT_000d + 1;
    }
  } while (DAT_000d < 4);
  return;
}

