
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d3ee(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  bVar1 = 0xf;
  do {
    *(undefined1 *)(bVar1 + 0x580) = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  DAT_0010 = (&DAT_0664)[DAT_050a];
  uStack0000 = 0xd4;
  officer_address();
  DAT_0011 = *(byte *)(_DAT_0000 + 0xb) >> 4;
  if (((((DAT_0010 == -0x5f) || (DAT_0010 == 'c')) || (DAT_0010 == -0x59)) ||
      (((((DAT_0010 == '\x16' || (DAT_0010 == -0x3c)) ||
         ((DAT_0010 == -0x25 || ((DAT_0010 == -0x16 || (DAT_0010 == 'k')))))) || (DAT_0010 == -0x32)
        ) || ((DAT_0010 == -0x15 || (DAT_0010 == -0x49)))))) && (2 < DAT_0011)) {
    cVar2 = '\x05';
    goto LAB_d4e6;
  }
  if (((((DAT_0010 == '\x18') || (DAT_0010 == '7')) || (DAT_0010 == 'p')) ||
      ((DAT_0010 == -0x2b || (DAT_0010 == 'n')))) || (DAT_0010 == 'g')) {
    if (3 < DAT_0011) {
      cVar2 = '\x06';
      goto LAB_d4e6;
    }
    if (2 < DAT_0011) {
      cVar2 = '\x05';
      goto LAB_d4e6;
    }
  }
  if (((DAT_0010 == -0x3b) || (DAT_0010 == 'V')) || (DAT_0010 == ']')) {
    if (4 < DAT_0011) {
      cVar2 = '\a';
      goto LAB_d4e6;
    }
    if (3 < DAT_0011) {
      cVar2 = '\x06';
      goto LAB_d4e6;
    }
    if (2 < DAT_0011) {
      cVar2 = '\x05';
      goto LAB_d4e6;
    }
  }
  if (DAT_0010 == 'm') {
    cVar2 = '\b';
    if ((((5 < DAT_0011) || (cVar2 = '\a', 4 < DAT_0011)) || (cVar2 = '\x06', 3 < DAT_0011)) ||
       (cVar2 = '\x05', 2 < DAT_0011)) goto LAB_d4e6;
  }
  uStack0000 = 0xd4;
  officer_address(DAT_0010);
  bVar1 = *(byte *)(_DAT_0000 + 2);
  cVar2 = '\0';
  if (((0x27 < bVar1) && (cVar2 = '\x01', 0x3b < bVar1)) &&
     ((cVar2 = '\x02', 0x4a < bVar1 && (cVar2 = '\x03', 0x54 < bVar1)))) {
    cVar2 = '\x04';
  }
LAB_d4e6:
  _DAT_0000 = CONCAT11((&DAT_d50a)[(byte)(cVar2 << 1)],(&DAT_d509)[(byte)(cVar2 << 1)]);
  for (bVar1 = 0; *(char *)(_DAT_0000 + (ushort)bVar1) != -1; bVar1 = bVar1 + 1) {
    *(char *)(bVar1 + 0x580) = *(char *)(_DAT_0000 + (ushort)bVar1);
  }
  DAT_0542 = bVar1 - 1;
  return;
}

