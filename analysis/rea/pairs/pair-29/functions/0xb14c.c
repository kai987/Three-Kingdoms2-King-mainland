
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b14c(byte param_1)

{
  undefined1 uVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  
  DAT_0005 = '\0';
  if (DAT_0150 < '\0') {
    DAT_0005 = 'p';
  }
  DAT_0007 = '@';
  DAT_0006 = '\0';
  if (param_1 != 1) {
    DAT_0007 = -0x80;
    DAT_0006 = ' ';
  }
  bVar3 = (&DAT_037c)[param_1] * '\x02';
  bVar4 = bVar3 + (&DAT_037c)[param_1];
  bVar2 = bVar4 * '\x04' + (&DAT_037c)[param_1];
  _DAT_0000 = (undefined1 *)
              CONCAT11((((CARRY1(bVar3,(&DAT_037c)[param_1]) - ((char)(&DAT_037c)[param_1] >> 7)) *
                         '\x02' | bVar4 >> 7) << 1 | (bVar4 & 0x7f) >> 6) +
                       CARRY1(bVar4 * '\x04',(&DAT_037c)[param_1]) + -0x73 + (0x4b < bVar2),
                       bVar2 + 0xb4);
  _DAT_0002 = &DAT_b222;
  bVar4 = 0;
  DAT_0004 = 0;
  uVar1 = *_DAT_0000;
  *(undefined1 *)(param_1 + 0xae) = uVar1;
  *(undefined1 *)(param_1 + 0xbe) = uVar1;
  *(undefined1 *)(param_1 + 0xc6) = uVar1;
  *(undefined1 *)(param_1 + 0xce) = uVar1;
  *(undefined1 *)(param_1 + 0xd6) = uVar1;
  do {
    bVar4 = bVar4 + 1;
    if (_DAT_0000[bVar4] == -1) {
      return;
    }
    *(char *)(DAT_007c + 0x201) = _DAT_0000[bVar4] + DAT_0007;
    *(undefined1 *)(DAT_007c + 0x202) = 1;
    *(char *)(DAT_007c + 0x203) = _DAT_0002[DAT_0004] + DAT_0005;
    *(char *)(DAT_007c + 0x200) = _DAT_0002[(byte)(DAT_0004 + 1)] + DAT_0006;
    DAT_0004 = DAT_0004 + 2;
    DAT_007c = DAT_007c + 4;
  } while (bVar4 < 0xc);
  return;
}

