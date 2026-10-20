// Ghidra-generated fixed-bank-pair pseudocode. Bank switching and inline pointer dispatch need manual correction. Not original source.

/* 0xa000 bank14_entry_00 */

/* WARNING: Control flow encountered bad instruction data */

void bank14_entry_00(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_c01b();
  DAT_057b = 0;
  uStack0000 = 0xa0;
  FUN_a030();
  uStack0000 = DAT_0081;
  DAT_0081 = DAT_057b;
  far_call_inline_word(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa003 thunk_FUN_d8d4 */

/* WARNING: Removing unreachable block (RAM,0xd99b) */
/* WARNING: Removing unreachable block (RAM,0xd9bd) */
/* WARNING: Removing unreachable block (RAM,0xd9c8) */
/* WARNING: Removing unreachable block (RAM,0xd9f9) */
/* WARNING: Removing unreachable block (RAM,0xd9cc) */
/* WARNING: Removing unreachable block (RAM,0xda03) */
/* WARNING: Removing unreachable block (RAM,0xda05) */
/* WARNING: Removing unreachable block (RAM,0xda0a) */
/* WARNING: Removing unreachable block (RAM,0xda15) */
/* WARNING: Removing unreachable block (RAM,0xd9d0) */
/* WARNING: Removing unreachable block (RAM,0xda18) */
/* WARNING: Removing unreachable block (RAM,0xda22) */
/* WARNING: Removing unreachable block (RAM,0xda29) */
/* WARNING: Removing unreachable block (RAM,0xda34) */
/* WARNING: Removing unreachable block (RAM,0xd9d4) */
/* WARNING: Removing unreachable block (RAM,0xd9d8) */
/* WARNING: Removing unreachable block (RAM,0xd9df) */
/* WARNING: Removing unreachable block (RAM,0xdb34) */
/* WARNING: Removing unreachable block (RAM,0xdb3e) */
/* WARNING: Removing unreachable block (RAM,0xdb45) */
/* WARNING: Removing unreachable block (RAM,0xdb4a) */
/* WARNING: Removing unreachable block (RAM,0xdb51) */
/* WARNING: Removing unreachable block (RAM,0xdb56) */
/* WARNING: Removing unreachable block (RAM,0xdb6c) */
/* WARNING: Removing unreachable block (RAM,0xdb70) */
/* WARNING: Removing unreachable block (RAM,0xdb79) */
/* WARNING: Removing unreachable block (RAM,0xdb7d) */
/* WARNING: Removing unreachable block (RAM,0xdb7f) */
/* WARNING: Removing unreachable block (RAM,0xdb81) */
/* WARNING: Removing unreachable block (RAM,0xdb86) */
/* WARNING: Removing unreachable block (RAM,0xdb8c) */
/* WARNING: Removing unreachable block (RAM,0xdb8d) */
/* WARNING: Removing unreachable block (RAM,0xdb3b) */
/* WARNING: Removing unreachable block (RAM,0xdbf0) */
/* WARNING: Removing unreachable block (RAM,0xdb31) */
/* WARNING: Removing unreachable block (RAM,0xdbe6) */
/* WARNING: Removing unreachable block (RAM,0xdb96) */
/* WARNING: Removing unreachable block (RAM,0xdba8) */
/* WARNING: Removing unreachable block (RAM,0xdbb4) */
/* WARNING: Removing unreachable block (RAM,0xdbc3) */
/* WARNING: Removing unreachable block (RAM,0xdbc9) */
/* WARNING: Removing unreachable block (RAM,0xdbd9) */
/* WARNING: Removing unreachable block (RAM,0xdbd1) */
/* WARNING: Removing unreachable block (RAM,0xdbd5) */
/* WARNING: Removing unreachable block (RAM,0xdbdb) */
/* WARNING: Removing unreachable block (RAM,0xd9dc) */
/* WARNING: Removing unreachable block (RAM,0xda76) */
/* WARNING: Removing unreachable block (RAM,0xda7a) */
/* WARNING: Removing unreachable block (RAM,0xda82) */
/* WARNING: Removing unreachable block (RAM,0xda9c) */
/* WARNING: Removing unreachable block (RAM,0xdabc) */
/* WARNING: Removing unreachable block (RAM,0xdacb) */
/* WARNING: Removing unreachable block (RAM,0xdaf8) */
/* WARNING: Removing unreachable block (RAM,0xdb08) */
/* WARNING: Removing unreachable block (RAM,0xdb0c) */
/* WARNING: Removing unreachable block (RAM,0xdb1e) */
/* WARNING: Removing unreachable block (RAM,0xdafc) */
/* WARNING: Removing unreachable block (RAM,0xdacf) */
/* WARNING: Removing unreachable block (RAM,0xdaf5) */
/* WARNING: Removing unreachable block (RAM,0xdb05) */
/* WARNING: Removing unreachable block (RAM,0xdaa0) */
/* WARNING: Removing unreachable block (RAM,0xdaa4) */
/* WARNING: Removing unreachable block (RAM,0xdac0) */
/* WARNING: Removing unreachable block (RAM,0xda86) */
/* WARNING: Removing unreachable block (RAM,0xda8b) */
/* WARNING: Removing unreachable block (RAM,0xda67) */
/* WARNING: Removing unreachable block (RAM,0xda7f) */
/* WARNING: Removing unreachable block (RAM,0xda6c) */
/* WARNING: Removing unreachable block (RAM,0xda93) */
/* WARNING: Removing unreachable block (RAM,0xda37) */
/* WARNING: Removing unreachable block (RAM,0xda3b) */
/* WARNING: Removing unreachable block (RAM,0xda40) */
/* WARNING: Removing unreachable block (RAM,0xda46) */
/* WARNING: Removing unreachable block (RAM,0xda48) */
/* WARNING: Removing unreachable block (RAM,0xda4d) */
/* WARNING: Removing unreachable block (RAM,0xda53) */
/* WARNING: Removing unreachable block (RAM,0xda55) */
/* WARNING: Removing unreachable block (RAM,0xda58) */
/* WARNING: Removing unreachable block (RAM,0xda5c) */
/* WARNING: Removing unreachable block (RAM,0xda5f) */
/* WARNING: Removing unreachable block (RAM,0xda62) */
/* WARNING: Removing unreachable block (RAM,0xd9e2) */
/* WARNING: Removing unreachable block (RAM,0xd9ef) */
/* WARNING: Removing unreachable block (RAM,0xd9f3) */
/* WARNING: Removing unreachable block (RAM,0xdbf1) */
/* WARNING: Removing unreachable block (RAM,0xdbfb) */
/* WARNING: Removing unreachable block (RAM,0xdbfd) */
/* WARNING: Removing unreachable block (RAM,0xd9e6) */
/* WARNING: Removing unreachable block (RAM,0xd9ec) */

void thunk_FUN_d8d4(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xd8;
  FUN_f25f(0x22);
  DAT_00e2 = 0x23;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  uRAMe800 = 0xe3;
  bVar1 = 0;
  DAT_07f2 = 0;
  DAT_07f9 = DAT_07f9 + '\x01';
  do {
    DAT_07f3 = *(byte *)(bVar1 + 0x701) & 7;
    DAT_07f5 = DAT_07f3 << 2;
    DAT_07f4 = (&DAT_dd56)[DAT_07f3];
    if (*(char *)(bVar1 + 0x700) == '\0') {
      DAT_00f0 = (byte *)CONCAT11(*(undefined1 *)(bVar1 + 0x703),*(undefined1 *)(bVar1 + 0x702));
      bVar2 = *DAT_00f0;
      *(byte *)(bVar1 + 0x704) = bVar2 & 0xf;
      *(byte *)(bVar1 + 0x705) = bVar2 & 0xf;
      cVar3 = '\x01';
      uStack0000 = 0xd9;
      FUN_dc3f();
      bVar2 = DAT_00f0[(byte)(cVar3 + 1)] | DAT_07f7;
      *(byte *)(bVar1 + 0x706) = bVar2;
      *(byte *)(bVar1 + 0x707) = bVar2;
      *(byte *)(bVar1 + 0x709) = DAT_00f0[(byte)(cVar3 + 2)];
      *(undefined1 *)(bVar1 + 0x70a) = 0;
      *(undefined1 *)(bVar1 + 0x70b) = 0;
      *(undefined1 *)(bVar1 + 0x70c) = 0;
      *(undefined1 *)(bVar1 + 0x70f) = 0;
      *(undefined1 *)(bVar1 + 0x700) = 2;
LAB_d940:
      uStack0000 = 0xd9;
      FUN_d99b();
LAB_d943:
      DAT_07f2 = (&DAT_dd4e)[DAT_07f3] | DAT_07f2;
    }
    else if (*(char *)(bVar1 + 0x700) != -1) {
      uStack0000 = 0xd9;
      FUN_dcd8();
      *(char *)(bVar1 + 0x70e) = *(char *)(bVar1 + 0x70e) + '\x01';
      if (*(byte *)(bVar1 + 0x70d) <= *(byte *)(bVar1 + 0x70e)) {
        *(undefined1 *)(bVar1 + 0x70e) = *(undefined1 *)(bVar1 + 0x70d);
      }
      cVar3 = *(char *)(bVar1 + 0x705) + -1;
      *(char *)(bVar1 + 0x705) = cVar3;
      if (cVar3 < '\0') {
        *(byte *)(bVar1 + 0x705) = *(byte *)(bVar1 + 0x704) & 0xf;
        uStack0000 = 0xd9;
        FUN_dc90();
        if (*(char *)(bVar1 + 0x715) != '\0') {
          *(char *)(bVar1 + 0x715) = *(char *)(bVar1 + 0x715) + -1;
        }
        cVar3 = *(char *)(bVar1 + 0x708) + -1;
        *(char *)(bVar1 + 0x708) = cVar3;
        if (cVar3 == '\0') goto LAB_d940;
      }
      uStack0000 = 0xd9;
      FUN_df6e();
      goto LAB_d943;
    }
    bVar1 = bVar1 + 0x16;
    if (bVar1 == 0xf2) {
      return;
    }
  } while( true );
}



/* 0xa006 thunk_FUN_d7fb */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_d7fb(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xd8;
  officer_address(DAT_000a);
  DAT_000b = DAT_000b >> 1 | DAT_000c << 7;
  bVar4 = CARRY1(*(byte *)(_DAT_0000 + 6),DAT_000b);
  DAT_000d = *(byte *)(_DAT_0000 + 6) + DAT_000b;
  DAT_000c = DAT_000c >> 1;
  *(byte *)(_DAT_0000 + 6) = DAT_000d;
  DAT_000e = *(char *)(_DAT_0000 + 7) + DAT_000c + bVar4;
  *(byte *)(_DAT_0000 + 7) = DAT_000e;
  bVar2 = (*(byte *)(_DAT_0000 + 7) + 0x3d) -
          ((*(byte *)(_DAT_0000 + 6) + 0xb1 & ~*(byte *)(_DAT_0000 + 6) & 0x80) == 0);
  bVar1 = ~*(byte *)(_DAT_0000 + 7);
  if (((bVar1 & 0xc3 | bVar2 & 0xc3 | bVar2 & bVar1) & 0x80) != 0) {
    *(undefined1 *)(_DAT_0000 + 6) = 0x4f;
    *(undefined1 *)(_DAT_0000 + 7) = 0xc3;
  }
  bVar1 = (*(byte *)(_DAT_0000 + 0xb) & 0xf0) >> 3;
  if (((bVar1 < 0xe) &&
      (bVar2 = DAT_000d - (&DAT_d85b)[bVar1],
      bVar2 = (DAT_000e - (&DAT_d85c)[bVar1]) -
              ((((&DAT_d85b)[bVar1] & (~DAT_000d | bVar2) | bVar2 & ~DAT_000d) & 0x80) == 0),
      (((&DAT_d85c)[bVar1] & (~DAT_000e | bVar2) | bVar2 & ~DAT_000e) & 0x80) != 0)) &&
     (DAT_000f = ((*(byte *)(_DAT_0000 + 0xb) >> 4) + 1) * '\x10',
     (*(byte *)(_DAT_0000 + 0xb) & 0xf0) < DAT_000f)) {
    *(byte *)(_DAT_0000 + 0xb) = *(byte *)(_DAT_0000 + 0xb) & 0xf | DAT_000f;
    bVar1 = *(byte *)(_DAT_0000 + 1);
    cVar3 = '\x06';
    if (((bVar1 < 0x33) || (cVar3 = '\x05', bVar1 < 0x47)) ||
       ((cVar3 = '\x04', bVar1 < 0x51 || (cVar3 = '\x02', bVar1 < 0x5a)))) {
      *(char *)(_DAT_0000 + 1) = cVar3 + *(char *)(_DAT_0000 + 1);
    }
    return;
  }
  DAT_000f = 0;
  return;
}



/* 0xa009 thunk_FUN_d8b0 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_d8b0(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd8;
  officer_address(DAT_000b);
  DAT_000c = CARRY1(*(byte *)(_DAT_0000 + 1),*(byte *)(_DAT_0000 + 2));
  DAT_000b = *(byte *)(_DAT_0000 + 1) + *(byte *)(_DAT_0000 + 2);
  FUN_d7fb();
  return;
}



/* 0xa00c thunk_FUN_df6e */

void thunk_FUN_df6e(byte param_1)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xdf;
  FUN_dc31();
  if ((DAT_07f4 & 0x80) == 0x80) {
    *(undefined1 *)(DAT_07f5 + 0x4000) = *(undefined1 *)(param_1 + 0x706);
    return;
  }
  if (*(char *)(param_1 + 0x70c) != '\0') {
    FUN_dc59();
    return;
  }
  if (DAT_07f5 < 0x10) {
    *(byte *)(DAT_07f5 + 0x4000) =
         (*(byte *)(param_1 + 0x706) & 0x10) << 1 | *(byte *)(param_1 + 0x706);
    return;
  }
  LAB_f800 = (DAT_07f5 << 1 | 0x67) - 1;
  DAT_4800 = (*(byte *)(param_1 + 0x706) & 0xc0) >> 3;
  return;
}



/* 0xa00f FUN_a00f */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a00f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_c01b();
  DAT_057b = 0;
  uStack0000 = 0xa0;
  FUN_a030();
  uStack0000 = DAT_0081;
  DAT_0081 = DAT_057b;
  far_call_inline_word(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa01e FUN_a01e */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a01e(void)

{
  undefined1 uStack0000;
  
  DAT_0081 = DAT_057b;
  uStack0000 = 0xa0;
  far_call_inline_word(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa024 FUN_a024 */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a024(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  far_call_inline_word(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xa030 FUN_a030 */

void FUN_a030(void)

{
  undefined1 uStack0000;
  
  if (((DAT_0540 != '\0') && (DAT_0540 != '\x01')) && (DAT_0540 != '\x02')) {
    FUN_a069();
    return;
  }
  DAT_0000 = DAT_0560;
  DAT_000a = 0xa5;
  uStack0000 = 0xa0;
  far_call_inline_word(0);
  uStack0000 = 0xa0;
  (*(code *)IRQ)();
  return;
}



/* 0xa045 FUN_a045 */

void FUN_a045(void)

{
  undefined1 uStack0000;
  
  DAT_000a = 0xa5;
  uStack0000 = 0xa0;
  far_call_inline_word(0);
  uStack0000 = 0xa0;
  (*(code *)IRQ)();
  return;
}



/* 0xa069 FUN_a069 */

/* WARNING: Control flow encountered bad instruction data */

void FUN_a069(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  DAT_00a0 = tail_dispatch_inline_table(DAT_0540);
                    /* WARNING: Bad instruction - Truncating control flow here */
  halt_baddata();
}



/* 0xc01b FUN_c01b */

void FUN_c01b(void)

{
  byte bVar1;
  
  bVar1 = DAT_005e >> 3 & 3;
  if (DAT_0544 == '\x03') {
    bVar1 = bVar1 + 4;
  }
  DAT_00b3 = (&DAT_c054)[bVar1];
  DAT_00c3 = DAT_00b3;
  DAT_00cb = DAT_00b3;
  DAT_00d3 = DAT_00b3;
  DAT_00db = DAT_00b3;
  DAT_00b5 = (&DAT_c05c)[bVar1];
  DAT_00c5 = DAT_00b5;
  DAT_00cd = DAT_00b5;
  DAT_00d5 = DAT_00b5;
  DAT_00dd = DAT_00b5;
  return;
}



/* 0xd7fb FUN_d7fb */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d7fb(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  undefined1 uStack0000;
  
  uStack0000 = 0xd8;
  officer_address(DAT_000a);
  DAT_000b = DAT_000b >> 1 | DAT_000c << 7;
  bVar4 = CARRY1(*(byte *)(_DAT_0000 + 6),DAT_000b);
  DAT_000d = *(byte *)(_DAT_0000 + 6) + DAT_000b;
  DAT_000c = DAT_000c >> 1;
  *(byte *)(_DAT_0000 + 6) = DAT_000d;
  DAT_000e = *(char *)(_DAT_0000 + 7) + DAT_000c + bVar4;
  *(byte *)(_DAT_0000 + 7) = DAT_000e;
  bVar2 = (*(byte *)(_DAT_0000 + 7) + 0x3d) -
          ((*(byte *)(_DAT_0000 + 6) + 0xb1 & ~*(byte *)(_DAT_0000 + 6) & 0x80) == 0);
  bVar1 = ~*(byte *)(_DAT_0000 + 7);
  if (((bVar1 & 0xc3 | bVar2 & 0xc3 | bVar2 & bVar1) & 0x80) != 0) {
    *(undefined1 *)(_DAT_0000 + 6) = 0x4f;
    *(undefined1 *)(_DAT_0000 + 7) = 0xc3;
  }
  bVar1 = (*(byte *)(_DAT_0000 + 0xb) & 0xf0) >> 3;
  if (((bVar1 < 0xe) &&
      (bVar2 = DAT_000d - (&DAT_d85b)[bVar1],
      bVar2 = (DAT_000e - (&DAT_d85c)[bVar1]) -
              ((((&DAT_d85b)[bVar1] & (~DAT_000d | bVar2) | bVar2 & ~DAT_000d) & 0x80) == 0),
      (((&DAT_d85c)[bVar1] & (~DAT_000e | bVar2) | bVar2 & ~DAT_000e) & 0x80) != 0)) &&
     (DAT_000f = ((*(byte *)(_DAT_0000 + 0xb) >> 4) + 1) * '\x10',
     (*(byte *)(_DAT_0000 + 0xb) & 0xf0) < DAT_000f)) {
    *(byte *)(_DAT_0000 + 0xb) = *(byte *)(_DAT_0000 + 0xb) & 0xf | DAT_000f;
    bVar1 = *(byte *)(_DAT_0000 + 1);
    cVar3 = '\x06';
    if (((bVar1 < 0x33) || (cVar3 = '\x05', bVar1 < 0x47)) ||
       ((cVar3 = '\x04', bVar1 < 0x51 || (cVar3 = '\x02', bVar1 < 0x5a)))) {
      *(char *)(_DAT_0000 + 1) = cVar3 + *(char *)(_DAT_0000 + 1);
    }
    return;
  }
  DAT_000f = 0;
  return;
}



/* 0xd8b0 FUN_d8b0 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d8b0(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd8;
  officer_address(DAT_000b);
  DAT_000c = CARRY1(*(byte *)(_DAT_0000 + 1),*(byte *)(_DAT_0000 + 2));
  DAT_000b = *(byte *)(_DAT_0000 + 1) + *(byte *)(_DAT_0000 + 2);
  FUN_d7fb();
  return;
}



/* 0xd8d4 FUN_d8d4 */

/* WARNING: Removing unreachable block (RAM,0xd99b) */
/* WARNING: Removing unreachable block (RAM,0xd9bd) */
/* WARNING: Removing unreachable block (RAM,0xd9c8) */
/* WARNING: Removing unreachable block (RAM,0xd9f9) */
/* WARNING: Removing unreachable block (RAM,0xd9cc) */
/* WARNING: Removing unreachable block (RAM,0xda03) */
/* WARNING: Removing unreachable block (RAM,0xda05) */
/* WARNING: Removing unreachable block (RAM,0xda0a) */
/* WARNING: Removing unreachable block (RAM,0xda15) */
/* WARNING: Removing unreachable block (RAM,0xd9d0) */
/* WARNING: Removing unreachable block (RAM,0xda18) */
/* WARNING: Removing unreachable block (RAM,0xda22) */
/* WARNING: Removing unreachable block (RAM,0xda29) */
/* WARNING: Removing unreachable block (RAM,0xda34) */
/* WARNING: Removing unreachable block (RAM,0xd9d4) */
/* WARNING: Removing unreachable block (RAM,0xd9d8) */
/* WARNING: Removing unreachable block (RAM,0xd9df) */
/* WARNING: Removing unreachable block (RAM,0xdb34) */
/* WARNING: Removing unreachable block (RAM,0xdb3e) */
/* WARNING: Removing unreachable block (RAM,0xdb45) */
/* WARNING: Removing unreachable block (RAM,0xdb4a) */
/* WARNING: Removing unreachable block (RAM,0xdb51) */
/* WARNING: Removing unreachable block (RAM,0xdb56) */
/* WARNING: Removing unreachable block (RAM,0xdb6c) */
/* WARNING: Removing unreachable block (RAM,0xdb70) */
/* WARNING: Removing unreachable block (RAM,0xdb79) */
/* WARNING: Removing unreachable block (RAM,0xdb7d) */
/* WARNING: Removing unreachable block (RAM,0xdb7f) */
/* WARNING: Removing unreachable block (RAM,0xdb81) */
/* WARNING: Removing unreachable block (RAM,0xdb86) */
/* WARNING: Removing unreachable block (RAM,0xdb8c) */
/* WARNING: Removing unreachable block (RAM,0xdb8d) */
/* WARNING: Removing unreachable block (RAM,0xdb3b) */
/* WARNING: Removing unreachable block (RAM,0xdbf0) */
/* WARNING: Removing unreachable block (RAM,0xdb31) */
/* WARNING: Removing unreachable block (RAM,0xdbe6) */
/* WARNING: Removing unreachable block (RAM,0xdb96) */
/* WARNING: Removing unreachable block (RAM,0xdba8) */
/* WARNING: Removing unreachable block (RAM,0xdbb4) */
/* WARNING: Removing unreachable block (RAM,0xdbc3) */
/* WARNING: Removing unreachable block (RAM,0xdbc9) */
/* WARNING: Removing unreachable block (RAM,0xdbd9) */
/* WARNING: Removing unreachable block (RAM,0xdbd1) */
/* WARNING: Removing unreachable block (RAM,0xdbd5) */
/* WARNING: Removing unreachable block (RAM,0xdbdb) */
/* WARNING: Removing unreachable block (RAM,0xd9dc) */
/* WARNING: Removing unreachable block (RAM,0xda76) */
/* WARNING: Removing unreachable block (RAM,0xda7a) */
/* WARNING: Removing unreachable block (RAM,0xda82) */
/* WARNING: Removing unreachable block (RAM,0xda9c) */
/* WARNING: Removing unreachable block (RAM,0xdabc) */
/* WARNING: Removing unreachable block (RAM,0xdacb) */
/* WARNING: Removing unreachable block (RAM,0xdaf8) */
/* WARNING: Removing unreachable block (RAM,0xdb08) */
/* WARNING: Removing unreachable block (RAM,0xdb0c) */
/* WARNING: Removing unreachable block (RAM,0xdb1e) */
/* WARNING: Removing unreachable block (RAM,0xdafc) */
/* WARNING: Removing unreachable block (RAM,0xdacf) */
/* WARNING: Removing unreachable block (RAM,0xdaf5) */
/* WARNING: Removing unreachable block (RAM,0xdb05) */
/* WARNING: Removing unreachable block (RAM,0xdaa0) */
/* WARNING: Removing unreachable block (RAM,0xdaa4) */
/* WARNING: Removing unreachable block (RAM,0xdac0) */
/* WARNING: Removing unreachable block (RAM,0xda86) */
/* WARNING: Removing unreachable block (RAM,0xda8b) */
/* WARNING: Removing unreachable block (RAM,0xda67) */
/* WARNING: Removing unreachable block (RAM,0xda7f) */
/* WARNING: Removing unreachable block (RAM,0xda6c) */
/* WARNING: Removing unreachable block (RAM,0xda93) */
/* WARNING: Removing unreachable block (RAM,0xda37) */
/* WARNING: Removing unreachable block (RAM,0xda3b) */
/* WARNING: Removing unreachable block (RAM,0xda40) */
/* WARNING: Removing unreachable block (RAM,0xda46) */
/* WARNING: Removing unreachable block (RAM,0xda48) */
/* WARNING: Removing unreachable block (RAM,0xda4d) */
/* WARNING: Removing unreachable block (RAM,0xda53) */
/* WARNING: Removing unreachable block (RAM,0xda55) */
/* WARNING: Removing unreachable block (RAM,0xda58) */
/* WARNING: Removing unreachable block (RAM,0xda5c) */
/* WARNING: Removing unreachable block (RAM,0xda5f) */
/* WARNING: Removing unreachable block (RAM,0xda62) */
/* WARNING: Removing unreachable block (RAM,0xd9e2) */
/* WARNING: Removing unreachable block (RAM,0xd9ef) */
/* WARNING: Removing unreachable block (RAM,0xd9f3) */
/* WARNING: Removing unreachable block (RAM,0xdbf1) */
/* WARNING: Removing unreachable block (RAM,0xdbfb) */
/* WARNING: Removing unreachable block (RAM,0xdbfd) */
/* WARNING: Removing unreachable block (RAM,0xd9e6) */
/* WARNING: Removing unreachable block (RAM,0xd9ec) */

void FUN_d8d4(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xd8;
  FUN_f25f(0x22);
  DAT_00e2 = 0x23;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  uRAMe800 = 0xe3;
  bVar1 = 0;
  DAT_07f2 = 0;
  DAT_07f9 = DAT_07f9 + '\x01';
  do {
    DAT_07f3 = *(byte *)(bVar1 + 0x701) & 7;
    DAT_07f5 = DAT_07f3 << 2;
    DAT_07f4 = (&DAT_dd56)[DAT_07f3];
    if (*(char *)(bVar1 + 0x700) == '\0') {
      DAT_00f0 = (byte *)CONCAT11(*(undefined1 *)(bVar1 + 0x703),*(undefined1 *)(bVar1 + 0x702));
      bVar2 = *DAT_00f0;
      *(byte *)(bVar1 + 0x704) = bVar2 & 0xf;
      *(byte *)(bVar1 + 0x705) = bVar2 & 0xf;
      cVar3 = '\x01';
      uStack0000 = 0xd9;
      FUN_dc3f();
      bVar2 = DAT_00f0[(byte)(cVar3 + 1)] | DAT_07f7;
      *(byte *)(bVar1 + 0x706) = bVar2;
      *(byte *)(bVar1 + 0x707) = bVar2;
      *(byte *)(bVar1 + 0x709) = DAT_00f0[(byte)(cVar3 + 2)];
      *(undefined1 *)(bVar1 + 0x70a) = 0;
      *(undefined1 *)(bVar1 + 0x70b) = 0;
      *(undefined1 *)(bVar1 + 0x70c) = 0;
      *(undefined1 *)(bVar1 + 0x70f) = 0;
      *(undefined1 *)(bVar1 + 0x700) = 2;
LAB_d940:
      uStack0000 = 0xd9;
      FUN_d99b();
LAB_d943:
      DAT_07f2 = (&DAT_dd4e)[DAT_07f3] | DAT_07f2;
    }
    else if (*(char *)(bVar1 + 0x700) != -1) {
      uStack0000 = 0xd9;
      FUN_dcd8();
      *(char *)(bVar1 + 0x70e) = *(char *)(bVar1 + 0x70e) + '\x01';
      if (*(byte *)(bVar1 + 0x70d) <= *(byte *)(bVar1 + 0x70e)) {
        *(undefined1 *)(bVar1 + 0x70e) = *(undefined1 *)(bVar1 + 0x70d);
      }
      cVar3 = *(char *)(bVar1 + 0x705) + -1;
      *(char *)(bVar1 + 0x705) = cVar3;
      if (cVar3 < '\0') {
        *(byte *)(bVar1 + 0x705) = *(byte *)(bVar1 + 0x704) & 0xf;
        uStack0000 = 0xd9;
        FUN_dc90();
        if (*(char *)(bVar1 + 0x715) != '\0') {
          *(char *)(bVar1 + 0x715) = *(char *)(bVar1 + 0x715) + -1;
        }
        cVar3 = *(char *)(bVar1 + 0x708) + -1;
        *(char *)(bVar1 + 0x708) = cVar3;
        if (cVar3 == '\0') goto LAB_d940;
      }
      uStack0000 = 0xd9;
      FUN_df6e();
      goto LAB_d943;
    }
    bVar1 = bVar1 + 0x16;
    if (bVar1 == 0xf2) {
      return;
    }
  } while( true );
}



/* 0xd958 FUN_d958 */

/* WARNING: Removing unreachable block (RAM,0xd99b) */
/* WARNING: Removing unreachable block (RAM,0xd9bd) */
/* WARNING: Removing unreachable block (RAM,0xd9c8) */
/* WARNING: Removing unreachable block (RAM,0xd9f9) */
/* WARNING: Removing unreachable block (RAM,0xd9cc) */
/* WARNING: Removing unreachable block (RAM,0xda03) */
/* WARNING: Removing unreachable block (RAM,0xda05) */
/* WARNING: Removing unreachable block (RAM,0xda0a) */
/* WARNING: Removing unreachable block (RAM,0xda15) */
/* WARNING: Removing unreachable block (RAM,0xd9d0) */
/* WARNING: Removing unreachable block (RAM,0xda18) */
/* WARNING: Removing unreachable block (RAM,0xda22) */
/* WARNING: Removing unreachable block (RAM,0xda29) */
/* WARNING: Removing unreachable block (RAM,0xda34) */
/* WARNING: Removing unreachable block (RAM,0xd9d4) */
/* WARNING: Removing unreachable block (RAM,0xd9d8) */
/* WARNING: Removing unreachable block (RAM,0xd9df) */
/* WARNING: Removing unreachable block (RAM,0xdb34) */
/* WARNING: Removing unreachable block (RAM,0xdb3e) */
/* WARNING: Removing unreachable block (RAM,0xdb45) */
/* WARNING: Removing unreachable block (RAM,0xdb4a) */
/* WARNING: Removing unreachable block (RAM,0xdb51) */
/* WARNING: Removing unreachable block (RAM,0xdb56) */
/* WARNING: Removing unreachable block (RAM,0xdb6c) */
/* WARNING: Removing unreachable block (RAM,0xdb70) */
/* WARNING: Removing unreachable block (RAM,0xdb79) */
/* WARNING: Removing unreachable block (RAM,0xdb7d) */
/* WARNING: Removing unreachable block (RAM,0xdb7f) */
/* WARNING: Removing unreachable block (RAM,0xdb81) */
/* WARNING: Removing unreachable block (RAM,0xdb86) */
/* WARNING: Removing unreachable block (RAM,0xdb8c) */
/* WARNING: Removing unreachable block (RAM,0xdb8d) */
/* WARNING: Removing unreachable block (RAM,0xdb3b) */
/* WARNING: Removing unreachable block (RAM,0xdbf0) */
/* WARNING: Removing unreachable block (RAM,0xdb31) */
/* WARNING: Removing unreachable block (RAM,0xdbe6) */
/* WARNING: Removing unreachable block (RAM,0xdb96) */
/* WARNING: Removing unreachable block (RAM,0xdba8) */
/* WARNING: Removing unreachable block (RAM,0xdbb4) */
/* WARNING: Removing unreachable block (RAM,0xdbc3) */
/* WARNING: Removing unreachable block (RAM,0xdbc9) */
/* WARNING: Removing unreachable block (RAM,0xdbd9) */
/* WARNING: Removing unreachable block (RAM,0xdbd1) */
/* WARNING: Removing unreachable block (RAM,0xdbd5) */
/* WARNING: Removing unreachable block (RAM,0xdbdb) */
/* WARNING: Removing unreachable block (RAM,0xd9dc) */
/* WARNING: Removing unreachable block (RAM,0xda76) */
/* WARNING: Removing unreachable block (RAM,0xda7a) */
/* WARNING: Removing unreachable block (RAM,0xda82) */
/* WARNING: Removing unreachable block (RAM,0xda9c) */
/* WARNING: Removing unreachable block (RAM,0xdabc) */
/* WARNING: Removing unreachable block (RAM,0xdacb) */
/* WARNING: Removing unreachable block (RAM,0xdaf8) */
/* WARNING: Removing unreachable block (RAM,0xdb08) */
/* WARNING: Removing unreachable block (RAM,0xdb0c) */
/* WARNING: Removing unreachable block (RAM,0xdb1e) */
/* WARNING: Removing unreachable block (RAM,0xdafc) */
/* WARNING: Removing unreachable block (RAM,0xdacf) */
/* WARNING: Removing unreachable block (RAM,0xdaf5) */
/* WARNING: Removing unreachable block (RAM,0xdb05) */
/* WARNING: Removing unreachable block (RAM,0xdaa0) */
/* WARNING: Removing unreachable block (RAM,0xdaa4) */
/* WARNING: Removing unreachable block (RAM,0xdac0) */
/* WARNING: Removing unreachable block (RAM,0xda86) */
/* WARNING: Removing unreachable block (RAM,0xda8b) */
/* WARNING: Removing unreachable block (RAM,0xda67) */
/* WARNING: Removing unreachable block (RAM,0xda7f) */
/* WARNING: Removing unreachable block (RAM,0xda6c) */
/* WARNING: Removing unreachable block (RAM,0xda93) */
/* WARNING: Removing unreachable block (RAM,0xda37) */
/* WARNING: Removing unreachable block (RAM,0xda3b) */
/* WARNING: Removing unreachable block (RAM,0xda40) */
/* WARNING: Removing unreachable block (RAM,0xda46) */
/* WARNING: Removing unreachable block (RAM,0xda48) */
/* WARNING: Removing unreachable block (RAM,0xda4d) */
/* WARNING: Removing unreachable block (RAM,0xda53) */
/* WARNING: Removing unreachable block (RAM,0xda55) */
/* WARNING: Removing unreachable block (RAM,0xda58) */
/* WARNING: Removing unreachable block (RAM,0xda5c) */
/* WARNING: Removing unreachable block (RAM,0xda5f) */
/* WARNING: Removing unreachable block (RAM,0xda62) */
/* WARNING: Removing unreachable block (RAM,0xd9e2) */
/* WARNING: Removing unreachable block (RAM,0xd9ef) */
/* WARNING: Removing unreachable block (RAM,0xd9f3) */
/* WARNING: Removing unreachable block (RAM,0xdbf1) */
/* WARNING: Removing unreachable block (RAM,0xdbfb) */
/* WARNING: Removing unreachable block (RAM,0xdbfd) */
/* WARNING: Removing unreachable block (RAM,0xd9e6) */
/* WARNING: Removing unreachable block (RAM,0xd9ec) */

void FUN_d958(byte param_1)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
code_r0xd958:
  DAT_00f0 = (byte *)CONCAT11(*(undefined1 *)(param_1 + 0x703),*(undefined1 *)(param_1 + 0x702));
  bVar1 = *DAT_00f0;
  *(byte *)(param_1 + 0x704) = bVar1 & 0xf;
  *(byte *)(param_1 + 0x705) = bVar1 & 0xf;
  cVar2 = '\x01';
  uStack0000 = 0xd9;
  FUN_dc3f();
  bVar1 = DAT_00f0[(byte)(cVar2 + 1)] | DAT_07f7;
  *(byte *)(param_1 + 0x706) = bVar1;
  *(byte *)(param_1 + 0x707) = bVar1;
  *(byte *)(param_1 + 0x709) = DAT_00f0[(byte)(cVar2 + 2)];
  *(undefined1 *)(param_1 + 0x70a) = 0;
  *(undefined1 *)(param_1 + 0x70b) = 0;
  *(undefined1 *)(param_1 + 0x70c) = 0;
  *(undefined1 *)(param_1 + 0x70f) = 0;
  *(undefined1 *)(param_1 + 0x700) = 2;
LAB_d940:
  uStack0000 = 0xd9;
  FUN_d99b();
  do {
    DAT_07f2 = (&DAT_dd4e)[DAT_07f3] | DAT_07f2;
    do {
      param_1 = param_1 + 0x16;
      if (param_1 == 0xf2) {
        return;
      }
      DAT_07f3 = *(byte *)(param_1 + 0x701) & 7;
      DAT_07f5 = DAT_07f3 << 2;
      DAT_07f4 = (&DAT_dd56)[DAT_07f3];
      if (*(char *)(param_1 + 0x700) == '\0') goto code_r0xd958;
    } while (*(char *)(param_1 + 0x700) == -1);
    uStack0000 = 0xd9;
    FUN_dcd8();
    *(char *)(param_1 + 0x70e) = *(char *)(param_1 + 0x70e) + '\x01';
    if (*(byte *)(param_1 + 0x70d) <= *(byte *)(param_1 + 0x70e)) {
      *(undefined1 *)(param_1 + 0x70e) = *(undefined1 *)(param_1 + 0x70d);
    }
    cVar2 = *(char *)(param_1 + 0x705) + -1;
    *(char *)(param_1 + 0x705) = cVar2;
    if (cVar2 < '\0') {
      *(byte *)(param_1 + 0x705) = *(byte *)(param_1 + 0x704) & 0xf;
      uStack0000 = 0xd9;
      FUN_dc90();
      if (*(char *)(param_1 + 0x715) != '\0') {
        *(char *)(param_1 + 0x715) = *(char *)(param_1 + 0x715) + -1;
      }
      cVar2 = *(char *)(param_1 + 0x708) + -1;
      *(char *)(param_1 + 0x708) = cVar2;
      if (cVar2 == '\0') goto LAB_d940;
    }
    uStack0000 = 0xd9;
    FUN_df6e();
  } while( true );
}



/* 0xd99b FUN_d99b */

void FUN_d99b(byte param_1)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  undefined1 uVar6;
  byte bVar7;
  byte *pbVar8;
  bool bVar9;
  
code_r0xd99b:
  *(undefined1 *)(param_1 + 0x715) = *(undefined1 *)(param_1 + 0x714);
  bVar7 = *(char *)(param_1 + 0x700) * '\x02';
  DAT_00f0 = CONCAT11((*(char *)(param_1 + 0x703) - (*(char *)(param_1 + 0x700) >> 7)) +
                      CARRY1(bVar7,*(byte *)(param_1 + 0x702)),bVar7 + *(byte *)(param_1 + 0x702));
  bVar7 = 0xff;
LAB_d9bd:
  bVar3 = *(byte *)(DAT_00f0 + (ushort)(byte)(bVar7 + 1));
  *(char *)(param_1 + 0x700) = *(char *)(param_1 + 0x700) + '\x01';
  bVar7 = bVar7 + 2;
  if (0xef < bVar3) {
    if (bVar3 == 0xfd) {
      *(undefined1 *)(param_1 + 0x713) = *(undefined1 *)(param_1 + 0x700);
      goto LAB_d9bd;
    }
    if (bVar3 != 0xff) goto LAB_d9bd;
    *(undefined1 *)(param_1 + 0x700) = 0xff;
LAB_dbf1:
    bVar7 = *(byte *)(param_1 + 0x706) & 0xc0;
    if ((DAT_07f4 & 0x80) == 0x80) {
      bVar7 = 0;
    }
    *(byte *)(param_1 + 0x706) = bVar7;
    FUN_df6e();
    return;
  }
  if (bVar3 < 0xe0) {
    if (bVar3 < 0xd0) {
      if (0xbf < bVar3) {
        DAT_07f7 = bVar3 & 0xf;
        if (((DAT_07f4 & 0x80) != 0x80) && ((*(byte *)(param_1 + 0x706) & 0x10) != 0)) {
          *(undefined1 *)(param_1 + 0x70d) = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
          *(byte *)(param_1 + 0x70c) = DAT_07f7;
        }
        goto LAB_d9bd;
      }
      if (0xaf < bVar3) goto LAB_da37;
      if (0x9f < bVar3) {
        if (bVar3 == 0xa0) {
          if ((DAT_07f4 & 0x80) == 0x80) goto LAB_d9bd;
          bVar3 = *(byte *)(param_1 + 0x706) & 0xc0 | *(byte *)(DAT_00f0 + (ushort)bVar7);
        }
        else {
          if (bVar3 == 0xa1) {
            *(undefined1 *)(param_1 + 0x709) = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
            goto LAB_d9bd;
          }
          bVar9 = 0xa1 < bVar3;
          if (bVar3 != 0xa2) {
            if (bVar3 == 0xa3) {
              bVar3 = *(byte *)(DAT_00f0 + (ushort)bVar7);
              if (-1 < (char)bVar3) {
                *(byte *)register0x22 = bVar3;
                cVar2 = (bVar3 & 0xf) << 1;
                *(char *)(param_1 + 0x714) = cVar2;
                *(char *)(param_1 + 0x715) = cVar2;
                *(byte *)(param_1 + 0x701) =
                     *(byte *)register0x22 & 0x70 | *(byte *)(param_1 + 0x701) | 0x80;
                goto LAB_d9bd;
              }
            }
            else if (bVar3 != 0xa4) {
              if (bVar3 == 0xad) {
                *(undefined1 *)register0x22 = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
                bVar4 = *(byte *)(param_1 + 0x700) * '\x02';
                DAT_00f0 = CONCAT11(*(byte *)(param_1 + 0x700) >> 7,(char)DAT_00f0);
                bVar3 = *(byte *)(param_1 + 0x702);
                *(byte *)(param_1 + 0x702) = bVar4 + bVar3;
                *(char *)(param_1 + 0x703) =
                     *(char *)(param_1 + 0x703) + DAT_00f0._1_1_ + CARRY1(bVar4,bVar3);
                *(undefined1 *)(param_1 + 0x700) = 0;
                if (*(char *)register0x22 == '\0') {
                  FUN_d958();
                  return;
                }
              }
              else if (bVar3 == 0xae) {
                *(char *)(param_1 + 0x704) = *(char *)(param_1 + 0x704) << 1;
                *(byte *)(param_1 + 0x704) =
                     *(byte *)(param_1 + 0x704) >> 1 | *(byte *)(DAT_00f0 + (ushort)bVar7) & 0x80;
              }
              else if (bVar3 == 0xaf) {
                *(byte *)(param_1 + 0x705) = *(byte *)(DAT_00f0 + (ushort)bVar7) & 0xf;
                *(byte *)(param_1 + 0x704) =
                     *(byte *)(param_1 + 0x704) & 0xf0 | *(byte *)(param_1 + 0x705);
              }
              goto LAB_d9bd;
            }
            *(byte *)(param_1 + 0x701) = *(byte *)(param_1 + 0x701) & 7;
            goto LAB_d9bd;
          }
          *(byte *)((short)register0x22 + -1) = 0x89;
          *(byte *)((short)register0x22 + 0x10000) = 0xda;
          bVar3 = FUN_dc3f();
          if (!bVar9) {
            bVar3 = *(byte *)(param_1 + 0x706) & 0x1f | DAT_07f7;
          }
        }
        *(byte *)(param_1 + 0x706) = bVar3;
        *(byte *)(param_1 + 0x707) = bVar3;
        goto LAB_d9bd;
      }
      DAT_07f7 = bVar3;
      *(undefined1 *)(param_1 + 0x708) = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
      if ((DAT_07f4 & 0x40) != 0x40) {
        *(byte *)register0x22 = DAT_07f7;
        if (0xb < (DAT_07f7 & 0xf)) goto LAB_dbf1;
        bVar3 = (DAT_07f7 & 0xf) * '\x02';
        if (*(char *)(param_1 + 0x704) < '\0') {
          bVar3 = bVar3 + 0x18;
        }
        if (3 < DAT_07f3) {
          bVar3 = bVar3 + 0x30;
        }
        DAT_07f7 = (&DAT_dd06)[bVar3];
        bVar4 = *(byte *)register0x22 & 0x70;
        bVar7 = DAT_07f3;
        if (3 < DAT_07f3) {
          if (bVar4 == 0x40) {
            bVar4 = DAT_07f7 >> 7;
            DAT_07f7 = DAT_07f7 << 1;
            DAT_07f8 = (&DAT_dd07)[bVar3] << 1 | bVar4;
            goto LAB_db96;
          }
          bVar5 = (bVar4 - 0x30) - (bVar4 < 0x40);
          bVar1 = ~bVar4;
          bVar4 = 0;
          if (bVar5 != 0) {
            if ((bVar5 & bVar1 & 0x80) != 0) {
              bVar5 = 0xb0;
            }
            bVar4 = (bVar5 ^ 0xff) + 1;
          }
        }
        DAT_07f8 = (&DAT_dd07)[bVar3];
        for (bVar4 = bVar4 >> 4; bVar4 != 0; bVar4 = bVar4 - 1) {
          DAT_07f7 = DAT_07f7 >> 1 | DAT_07f8 << 7;
          bVar7 = 0;
          DAT_07f8 = DAT_07f8 >> 1;
        }
LAB_db96:
        *(undefined1 *)(param_1 + 0x70e) = 0;
        *(undefined1 *)(param_1 + 0x706) = *(undefined1 *)(param_1 + 0x707);
        *(byte *)((short)register0x22 + -1) = 0xa4;
        *(byte *)((short)register0x22 + 0x10000) = 0xdb;
        FUN_dc31();
        if (bVar7 < 4) {
          DAT_07f6 = (&DAT_dd4e)[bVar7] | DAT_07f6;
          DAT_4015 = DAT_07f6;
        }
        *(byte *)register0x22 = DAT_07f8;
        *(byte *)((short)register0x22 + -1) = DAT_07f7;
        *(byte *)((short)register0x22 + -3) = 0xbf;
        *(byte *)((short)register0x22 + -2) = 0xdb;
        FUN_df71();
        if (bVar7 < 0x10) {
          (&DAT_4001)[bVar7] = *(undefined1 *)(param_1 + 0x709);
        }
        uVar6 = *(byte *)((short)register0x22 + -1);
        *(byte *)((short)register0x22 + -2) = 0xcd;
        *(byte *)((short)register0x22 + -1) = 0xdb;
        bVar7 = FUN_dc03(uVar6);
        if (bVar7 < 2) {
          bVar7 = 2;
        }
        else if (0xfd < bVar7) {
          bVar7 = 0xfd;
        }
        *(byte *)(param_1 + 0x712) = bVar7;
        FUN_dc18(*(undefined1 *)register0x22);
        return;
      }
      if (DAT_07f7 < 0x10) {
        DAT_07f8 = 0;
        goto LAB_db96;
      }
      goto LAB_dbf1;
    }
    bVar3 = bVar3 & 0xf;
  }
  else {
    bVar3 = (bVar3 & 0xf ^ 0xff) + 1;
  }
  if ((DAT_07f4 & 0x80) != 0x80) {
    *(byte *)(param_1 + 0x70f) = bVar3;
    uVar6 = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
    *(undefined1 *)(param_1 + 0x710) = uVar6;
    *(undefined1 *)(param_1 + 0x711) = uVar6;
  }
  goto LAB_d9bd;
LAB_da37:
  if ((bVar3 & 0xf) != 0) {
    *(byte *)register0x22 = bVar3 & 0xf;
    pbVar8 = (byte *)((short)register0x22 + -1);
    if (*(char *)(DAT_00f0 + (ushort)bVar7) == '\0') {
      uVar6 = *(undefined1 *)register0x22;
      cVar2 = *(char *)(param_1 + 0x70a) + -1;
      *(char *)(param_1 + 0x70a) = cVar2;
      if (cVar2 == '\0') goto code_r0xd99b;
      if ((cVar2 >= '\0') ||
         (*(undefined1 *)(param_1 + 0x70a) = uVar6, pbVar8 = (byte *)register0x22, cVar2 < '\0'))
      goto LAB_da58;
    }
    register0x22 = (BADSPACEBASE *)(pbVar8 + 1);
    uVar6 = pbVar8[1];
    cVar2 = *(char *)(param_1 + 0x70b) + -1;
    *(char *)(param_1 + 0x70b) = cVar2;
    if (cVar2 == '\0') goto code_r0xd99b;
    register0x22 = (BADSPACEBASE *)(pbVar8 + 1);
    if (cVar2 < '\0') {
      *(undefined1 *)(param_1 + 0x70b) = uVar6;
      register0x22 = (BADSPACEBASE *)(pbVar8 + 1);
    }
  }
LAB_da58:
  cVar2 = *(char *)(DAT_00f0 + (ushort)bVar7);
  if (cVar2 == '\0') {
    cVar2 = *(char *)(param_1 + 0x713);
  }
  *(char *)(param_1 + 0x700) = cVar2;
  goto code_r0xd99b;
}



/* 0xdc03 FUN_dc03 */

void FUN_dc03(undefined1 param_1,byte param_2)

{
  if (param_2 < 0x10) {
    *(undefined1 *)(param_2 + 0x4002) = param_1;
    return;
  }
  LAB_f800 = param_2 << 1 | 0x60;
  DAT_4800 = param_1;
  return;
}



/* 0xdc18 FUN_dc18 */

void FUN_dc18(byte param_1,byte param_2)

{
  if (param_2 < 0x10) {
    *(byte *)(param_2 + 0x4003) = param_1 & 7 | 8;
    return;
  }
  LAB_f800 = param_2 << 1 | 0x62;
  DAT_4800 = param_1;
  return;
}



/* 0xdc31 FUN_dc31 */

byte FUN_dc31(void)

{
  byte bVar1;
  byte unaff_retaddr;
  
  bVar1 = (&DAT_dd4e)[DAT_07f3];
  if (((&DAT_dd4e)[DAT_07f3] & DAT_07f2) != 0) {
    bVar1 = unaff_retaddr;
  }
  return bVar1;
}



/* 0xdc3f FUN_dc3f */

void FUN_dc3f(byte param_1)

{
  if ((DAT_07f4 & 0x80) != 0x80) {
    DAT_07f7 = (*(byte *)(DAT_00f0 + (ushort)param_1) & 1) << 6 |
               (*(byte *)(DAT_00f0 + (ushort)param_1) >> 1) << 7;
    return;
  }
  DAT_07f7 = *(byte *)(DAT_00f0 + (ushort)param_1) & 0x7f;
  return;
}



/* 0xdc59 FUN_dc59 */

void FUN_dc59(char param_1,byte param_2)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  
  DAT_07f7 = 0;
  bVar2 = *(byte *)(param_2 + 0x70e);
  cVar3 = '\x03';
  do {
    bVar1 = bVar2 * '\x02';
    bVar4 = false;
    bVar2 = bVar1;
    if (*(byte *)(param_2 + 0x70d) <= bVar1) {
      bVar2 = bVar1 - *(byte *)(param_2 + 0x70d);
      bVar4 = ((*(byte *)(param_2 + 0x70d) & (~bVar1 | bVar2) | bVar2 & ~bVar1) & 0x80) != 0;
    }
    DAT_07f7 = DAT_07f7 << 1 | bVar4;
    cVar3 = cVar3 + -1;
  } while (-1 < cVar3);
  bVar2 = *(byte *)(param_2 + 0x706) & 0xc0;
  if (DAT_07f5 < 0x10) {
    *(byte *)(DAT_07f5 + 0x4000) =
         bVar2 | (&DAT_de6e)
                 [*(byte *)(param_2 + 0x706) & 0xf | (&DAT_ddce)[(byte)(param_1 << 4 | DAT_07f7)]];
    return;
  }
  LAB_f800 = (DAT_07f5 << 1 | 0x67) - 1;
  DAT_4800 = (bVar2 | (&DAT_de6e)
                      [*(byte *)(param_2 + 0x706) & 0xf |
                       (&DAT_ddce)[(byte)(param_1 << 4 | DAT_07f7)]] & 0xc0) >> 3;
  return;
}



/* 0xdc90 FUN_dc90 */

void FUN_dc90(byte param_1)

{
  char cVar1;
  
  if ((((DAT_07f4 & 0x80) != 0x80) && (*(char *)(param_1 + 0x70f) != '\0')) &&
     (cVar1 = *(char *)(param_1 + 0x711) + -1, *(char *)(param_1 + 0x711) = cVar1, cVar1 == '\0')) {
    *(undefined1 *)(param_1 + 0x711) = *(undefined1 *)(param_1 + 0x710);
    DAT_07f7 = *(byte *)(param_1 + 0x706) & 0x1f;
    if ((*(byte *)(param_1 + 0x706) & 0x10) != 0) {
      if (*(char *)(param_1 + 0x70f) < '\0') {
        *(char *)(param_1 + 0x70f) = *(char *)(param_1 + 0x70f) + '\x01';
        if (DAT_07f7 != 0x10) {
          *(char *)(param_1 + 0x706) = *(char *)(param_1 + 0x706) + -1;
          *(char *)(param_1 + 0x707) = *(char *)(param_1 + 0x707) + -1;
          return;
        }
      }
      else {
        *(char *)(param_1 + 0x70f) = *(char *)(param_1 + 0x70f) + -1;
        if (DAT_07f7 != 0x1f) {
          *(char *)(param_1 + 0x706) = *(char *)(param_1 + 0x706) + '\x01';
          *(char *)(param_1 + 0x707) = *(char *)(param_1 + 0x707) + '\x01';
        }
      }
    }
  }
  return;
}



/* 0xdcd8 FUN_dcd8 */

void FUN_dcd8(byte param_1)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xdc;
  FUN_dc31();
  if ((((DAT_07f4 & 0x40) != 0x40) && (*(char *)(param_1 + 0x715) == '\0')) &&
     ((char)*(byte *)(param_1 + 0x701) < '\0')) {
    DAT_07f7 = *(byte *)(param_1 + 0x701) & 0x70;
    *(char *)(DAT_07f5 + 0x4002) =
         (&DAT_dd5e)[DAT_07f9 & 0xf | DAT_07f7] + *(char *)(param_1 + 0x712);
  }
  return;
}



/* 0xdf6e FUN_df6e */

void FUN_df6e(byte param_1)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xdf;
  FUN_dc31();
  if ((DAT_07f4 & 0x80) == 0x80) {
    *(undefined1 *)(DAT_07f5 + 0x4000) = *(undefined1 *)(param_1 + 0x706);
    return;
  }
  if (*(char *)(param_1 + 0x70c) != '\0') {
    FUN_dc59();
    return;
  }
  if (DAT_07f5 < 0x10) {
    *(byte *)(DAT_07f5 + 0x4000) =
         (*(byte *)(param_1 + 0x706) & 0x10) << 1 | *(byte *)(param_1 + 0x706);
    return;
  }
  LAB_f800 = (DAT_07f5 << 1 | 0x67) - 1;
  DAT_4800 = (*(byte *)(param_1 + 0x706) & 0xc0) >> 3;
  return;
}



/* 0xdf71 FUN_df71 */

void FUN_df71(byte param_1)

{
  if ((DAT_07f4 & 0x80) == 0x80) {
    *(undefined1 *)(DAT_07f5 + 0x4000) = *(undefined1 *)(param_1 + 0x706);
    return;
  }
  if (*(char *)(param_1 + 0x70c) != '\0') {
    FUN_dc59();
    return;
  }
  if (DAT_07f5 < 0x10) {
    *(byte *)(DAT_07f5 + 0x4000) =
         (*(byte *)(param_1 + 0x706) & 0x10) << 1 | *(byte *)(param_1 + 0x706);
    return;
  }
  LAB_f800 = (DAT_07f5 << 1 | 0x67) - 1;
  DAT_4800 = (*(byte *)(param_1 + 0x706) & 0xc0) >> 3;
  return;
}



/* 0xe000 reset_dispatch */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void reset_dispatch(void)

{
  byte bVar1;
  char cVar2;
  
  cVar2 = '\x02';
  do {
    do {
    } while (-1 < DAT_2002);
    do {
    } while (DAT_2002 < '\0');
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  DAT_4010 = 0;
  DAT_4015 = 0xf;
  DAT_4017 = 0xc0;
  DAT_2000 = 0;
  DAT_2001 = 0;
  cVar2 = '\x04';
  do {
    do {
    } while (-1 < DAT_2002);
    do {
    } while (DAT_2002 < '\0');
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  _DAT_0001 = &DAT_0004;
  do {
    do {
      *_DAT_0001 = 0;
      cVar2 = DAT_0001 + '\x01';
      _DAT_0001 = (undefined1 *)CONCAT11(DAT_0002,cVar2);
    } while (cVar2 != '\0');
    bVar1 = DAT_0002 + 1;
    _DAT_0001 = (undefined1 *)((ushort)bVar1 << 8);
  } while (bVar1 < 8);
  *(undefined2 *)(CONCAT11((char)((ushort)&stack0x0000 >> 8),0xff) + -1) = 0xe061;
  FUN_f3bd();
  DAT_007a = 0;
  DAT_004e = (code *)CONCAT11(DAT_e07d,DAT_e07c);
                    /* WARNING: Could not recover jumptable at 0xe079. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_004e)();
  return;
}



/* 0xe370 FUN_e370 */

void FUN_e370(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe3;
  FUN_f237(0x3d);
  uStack0000 = 0xe3;
  func_0xa01b();
  uStack0000 = 0xe3;
  FUN_f206();
  return;
}



/* 0xe4da FUN_e4da */

void FUN_e4da(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe4;
  FUN_e768();
  uStack0000 = 0xe4;
  DAT_2001 = FUN_e74d();
  uStack0000 = 0xe4;
  FUN_e57f();
  uStack0000 = 0xe4;
  FUN_e7df();
  DAT_0090 = 0;
  DAT_0091 = 0;
  DAT_008e = 0;
  DAT_008f = 0;
  DAT_0098 = 0;
  DAT_0099 = 0;
  DAT_0096 = 0;
  DAT_0097 = 0;
  DAT_007e = 0;
  DAT_005e = 0;
  DAT_005f = 0;
  switchD_f878::caseD_f = 0;
  DAT_00a4 = 0;
  DAT_0300 = 0xff;
  DAT_0304 = 0xff;
  FUN_e823();
  return;
}



/* 0xe51f FUN_e51f */

void FUN_e51f(char param_1)

{
  byte bVar1;
  
  bVar1 = param_1 * '\b';
  DAT_00e6 = (&DAT_e567)[bVar1];
  DAT_c000 = (&DAT_e567)[bVar1];
  DAT_00e7 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_c800 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_00e8 = (&DAT_e567)[(byte)(bVar1 + 2)];
  DAT_d000 = (&DAT_e567)[(byte)(bVar1 + 2)];
  DAT_00e9 = (&DAT_e567)[(byte)(bVar1 + 3)];
  FUN_d7fb = (&DAT_e567)[(byte)(bVar1 + 3)];
  DAT_00ea = (&DAT_e567)[(byte)(bVar1 + 4)];
  DAT_00eb = (&DAT_e567)[(byte)(bVar1 + 5)];
  DAT_00ec = (&DAT_e567)[(byte)(bVar1 + 6)];
  DAT_00ed = (&DAT_e567)[(byte)(bVar1 + 7)];
  return;
}



/* 0xe57f FUN_e57f */

void FUN_e57f(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xe5;
  FUN_e673(0);
  uStack0000 = 0xe5;
  FUN_e590();
  DAT_00a5 = 0x4c;
  LAB_f800 = 0x4c;
  return;
}



/* 0xe590 FUN_e590 */

void FUN_e590(void)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  DAT_4015 = 0;
  DAT_07f6 = 0;
  DAT_4000 = 0x10;
  DAT_4004 = 0x10;
  DAT_400c = 0x10;
  DAT_4001 = 8;
  DAT_4005 = 8;
  DAT_4008 = 0;
  DAT_07f2 = 0;
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x700) = 0xff;
    *(undefined1 *)(bVar1 + 0x706) = 0;
    bVar1 = bVar1 + 0x16;
  } while (bVar1 != 0xf2);
  cVar2 = '?';
  do {
    cVar2 = cVar2 + -1;
  } while (-1 < cVar2);
  LAB_f800 = 0x80;
  bVar1 = 0;
  do {
    DAT_4800 = (&DAT_e6a6)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  uStack0000 = 0xe5;
  FUN_e5fa(0xf0,100);
  LAB_f800 = 0x7f;
  DAT_4800 = 0x30;
  return;
}



/* 0xe5f3 FUN_e5f3 */

void FUN_e5f3(undefined1 param_1,undefined1 param_2)

{
  LAB_f800 = param_2;
  DAT_4800 = param_1;
  return;
}



/* 0xe5fa FUN_e5fa */

undefined1 FUN_e5fa(undefined1 param_1,char param_2)

{
  undefined1 uVar1;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  do {
    uVar1 = uStack0000;
    uStack0000 = 0xe5;
    uStack0000 = FUN_e5f3(uVar1);
    param_2 = param_2 + '\b';
  } while (-1 < param_2);
  return uStack0000;
}



/* 0xe609 FUN_e609 */

undefined1 FUN_e609(undefined1 param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xe6;
  bVar1 = FUN_f25f(0x22);
  DAT_00f0 = (byte *)CONCAT11(((bVar1 >> 7) << 1 | (bVar1 & 0x7f) >> 6) + 0x80,bVar1 * '\x04');
  bVar1 = *DAT_00f0;
  if ((*(char *)(bVar1 + 0x700) != -1) && (*(byte *)(bVar1 + 0x701) < 4)) {
    DAT_07f6 = (&DAT_e667)[*(byte *)(bVar1 + 0x701)] & DAT_07f6;
    DAT_4015 = DAT_07f6;
  }
  *(byte *)(bVar1 + 0x701) = DAT_00f0[1];
  *(byte *)(bVar1 + 0x702) = DAT_00f0[2];
  *(byte *)(bVar1 + 0x703) = DAT_00f0[3] + 0x40;
  *(undefined1 *)(bVar1 + 0x700) = 0;
  return param_1;
}



/* 0xe673 FUN_e673 */

void FUN_e673(char param_1)

{
  char cStack0000;
  
  cStack0000 = param_1;
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  cStack0000 = cStack0000 + '\x01';
  FUN_e609();
  FUN_e609(cStack0000 + '\x01');
  return;
}



/* 0xe6c6 FUN_e6c6 */

void FUN_e6c6(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  
  bVar2 = DAT_0085;
  bVar1 = DAT_0083;
  DAT_0084 = DAT_0083;
  DAT_0086 = DAT_0085;
  DAT_4016 = 0;
  cVar3 = '\a';
  do {
    DAT_0083 = DAT_0083 >> 1;
    DAT_0085 = DAT_0085 >> 1 | ((DAT_4017 & 3) != 0) << 7;
    cVar3 = cVar3 + -1;
  } while (-1 < cVar3);
  DAT_0081 = (DAT_0083 ^ bVar1) & DAT_0083;
  DAT_0082 = (DAT_0085 ^ bVar2) & DAT_0085;
  return;
}



/* 0xe70e FUN_e70e */

void FUN_e70e(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  bVar1 = 0;
  DAT_007d = 0;
  do {
    DAT_2007 = (&DAT_0101)[bVar1];
    bVar1 = bVar1 + 2;
  } while (bVar1 < 0x20);
  DAT_2006 = 0;
  return;
}



/* 0xe749 FUN_e749 */

/* WARNING: Removing unreachable block (RAM,0xe74d) */

void FUN_e749(void)

{
  DAT_008c = 0x1e;
  return;
}



/* 0xe74d FUN_e74d */

void FUN_e74d(void)

{
  DAT_008c = 0;
  return;
}



/* 0xe753 FUN_e753 */

void FUN_e753(void)

{
  DAT_007b = 0;
  DAT_007e = 0;
  DAT_2000 = DAT_008b | 0x80;
  if (DAT_2000 == 0) {
    DAT_2000 = DAT_008b & 0x7f;
  }
  DAT_008b = DAT_2000;
  return;
}



/* 0xe768 FUN_e768 */

void FUN_e768(void)

{
  DAT_008b = DAT_008b & 0x7f;
  DAT_2000 = DAT_008b;
  return;
}



/* 0xe7b5 FUN_e7b5 */

void FUN_e7b5(void)

{
  char cVar1;
  byte bVar2;
  
  DAT_2006 = 0;
  cVar1 = '\0';
  DAT_0001 = '\x03';
  do {
    do {
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
    DAT_0001 = DAT_0001 + -1;
    bVar2 = 0;
  } while (DAT_0001 != '\0');
  do {
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0xc0);
  do {
    DAT_2007 = DAT_0003;
    bVar2 = bVar2 + 1;
  } while (bVar2 != 0);
  return;
}



/* 0xe7df FUN_e7df */

void FUN_e7df(void)

{
  undefined1 uStack0000;
  
  DAT_c000 = 0xe0;
  DAT_c800 = 0xe1;
  DAT_d000 = 0xe0;
  FUN_d7fb = 0xe1;
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  uStack0000 = 0xe8;
  FUN_e7b5(0x20);
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  uStack0000 = 0xe8;
  FUN_e7b5(0x24);
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  FUN_e7b5(0x28);
  return;
}



/* 0xe823 FUN_e823 */

void FUN_e823(void)

{
  byte bVar1;
  
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x200) = 0xf0;
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xe830 FUN_e830 */

void FUN_e830(void)

{
  byte bVar1;
  
  bVar1 = DAT_007c;
  if (DAT_007c != 0xff) {
    do {
      *(undefined1 *)(bVar1 + 0x200) = 0xf0;
      bVar1 = bVar1 + 4;
    } while (bVar1 != 0);
  }
  return;
}



/* 0xeade tail_dispatch_inline_table */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void tail_dispatch_inline_table(char param_1,undefined1 param_2)

{
  undefined1 unaff_retaddr;
  undefined1 unaff_retaddr_00;
  
  _DAT_0001 = CONCAT11(unaff_retaddr_00,unaff_retaddr);
  _DAT_0003 = (code *)CONCAT11(*(undefined1 *)(_DAT_0001 + (ushort)(byte)(param_1 * '\x02' + 2)),
                               *(undefined1 *)(_DAT_0001 + (ushort)(byte)(param_1 * '\x02' + 1)));
  DAT_0000 = param_2;
                    /* WARNING: Could not recover jumptable at 0xeaf4. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*_DAT_0003)(param_2);
  return;
}



/* 0xeaf7 FUN_eaf7 */

void FUN_eaf7(void)

{
  DAT_2005 = DAT_0090;
  DAT_008b = DAT_008f & 1 | DAT_008b & 0xfe;
  DAT_2000 = DAT_008b;
  return;
}



/* 0xec67 FUN_ec67 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ec67(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  
  if (DAT_0087 < '\0') {
    return;
  }
  if (-1 < (char)(DAT_008a + -1)) {
    DAT_008a = DAT_008a + -1;
    return;
  }
  DAT_008a = DAT_0089;
  DAT_007d = 1;
  if (DAT_0087 == '\0') {
    DAT_0088 = DAT_0088 - 1;
    if (DAT_0088 != 0) goto LAB_ec98;
  }
  else {
    DAT_0088 = DAT_0088 + 1;
    if (DAT_0088 < 4) goto LAB_ec98;
  }
  DAT_0087 = -1;
LAB_ec98:
  _DAT_0000 = 0x100;
  _DAT_0002 = &DAT_0120;
  bVar3 = 0x1f;
  do {
    cVar1 = _DAT_0002[bVar3];
    bVar2 = DAT_0088;
    do {
      bVar2 = bVar2 - 1;
      if ((char)bVar2 < '\0') goto LAB_ecb9;
      cVar1 = cVar1 + -0x10;
    } while (-1 < cVar1);
    cVar1 = '\x0f';
LAB_ecb9:
    *(char *)(_DAT_0000 + (ushort)bVar3) = cVar1;
    bVar3 = bVar3 - 1;
    if ((char)bVar3 < '\0') {
      return;
    }
  } while( true );
}



/* 0xecbf FUN_ecbf */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ecbf(void)

{
  byte bVar1;
  
  DAT_0087 = 0;
  DAT_0088 = 4;
  DAT_0089 = 4;
  _DAT_0000 = 0x100;
  _DAT_0002 = &DAT_0120;
  bVar1 = 0;
  do {
    _DAT_0002[bVar1] = *(undefined1 *)(_DAT_0000 + (ushort)bVar1);
    *(undefined1 *)(_DAT_0000 + (ushort)bVar1) = 0xf;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x20);
  return;
}



/* 0xee07 far_call_inline_word */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void far_call_inline_word(undefined1 param_1)

{
  undefined1 uStack0000;
  byte bStack0001;
  char cStack0002;
  
  DAT_0058 = DAT_00e2;
  _DAT_0059 = (undefined2 *)CONCAT11(cStack0002 + (0xfe < bStack0001),bStack0001 + 1);
  DAT_005b = (code *)*_DAT_0059;
  DAT_005d = param_1;
  FUN_f237(param_1);
  if ((char)(DAT_0059 + '\x01') == '\0') {
    DAT_005a = DAT_005a + '\x01';
  }
  uStack0000 = DAT_0058;
  DAT_0059 = DAT_0059 + '\x01';
                    /* WARNING: Could not recover jumptable at 0xee4a. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_005b)();
  return;
}



/* 0xee53 FUN_ee53 */

/* WARNING: Control flow encountered bad instruction data */

byte FUN_ee53(void)

{
  byte bVar1;
  byte bStack0000;
  
  if (DAT_007d == '\0') {
    if ((char)DAT_007e < '\0') {
      bStack0000 = DAT_007e;
      DAT_007e = DAT_007e & 0x7f;
      FUN_ef0b();
      return bStack0000;
    }
    bStack0000 = DAT_007e << 1;
    if ((char)bStack0000 < '\0') {
      DAT_007e = DAT_007e & 0xbf;
      FUN_ef71();
      return bStack0000;
    }
    if ((char)(DAT_007e << 2) < '\0') {
      DAT_007e = DAT_007e & 0xdf;
      bVar1 = FUN_efc0();
      return bVar1;
    }
    if ((char)(DAT_007e << 3) < '\0') {
      DAT_007e = DAT_007e & 0xef;
      bVar1 = FUN_f028();
      return bVar1;
    }
    if ((char)(DAT_007e << 4) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      DAT_007e = DAT_007e & 0xf7;
      bVar1 = thunk_FUN_df6e();
      return bVar1;
    }
    if ((char)(DAT_007e << 5) < '\0') {
      DAT_007e = DAT_007e & 0xfb;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      bVar1 = thunk_FUN_d7fb();
      return bVar1;
    }
    if ((char)(DAT_007e << 6) < '\0') {
      DAT_007e = DAT_007e & 0xfd;
      bStack0000 = 0xee;
      FUN_f237(0x3d);
      DAT_057b = 0;
      bStack0000 = 0xa0;
      FUN_a030();
      bStack0000 = DAT_0081;
      DAT_0081 = DAT_057b;
      far_call_inline_word(0x3d);
                    /* WARNING: Bad instruction - Truncating control flow here */
      halt_baddata();
    }
    if ((char)(DAT_007e << 7) < '\0') {
      bStack0000 = 0xee;
      FUN_f237(DAT_007e << 7,0x3d);
      bVar1 = bank14_entry_00();
      return bVar1;
    }
  }
  bVar1 = FUN_e70e();
  return bVar1;
}



/* 0xef0b FUN_ef0b */

void FUN_ef0b(void)

{
  byte bVar1;
  
  DAT_0001 = (((DAT_0140 & 3) << 1 | DAT_0141 >> 7) << 1 | (DAT_0141 & 0x7f) >> 6) << 1 |
             (DAT_0141 & 0x3f) >> 5;
  DAT_0000 = 0x1e - DAT_0001;
  DAT_2000 = DAT_008b | 4;
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0142)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_0141 & 0x1f;
  do {
    if (0x1d < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_0142)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xef71 FUN_ef71 */

void FUN_ef71(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0000 = 0x20 - (DAT_0165 & 0x1f);
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_0166)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_0165 & 0xe0;
  do {
    if (0x1f < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_0166)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xefc0 FUN_efc0 */

void FUN_efc0(void)

{
  byte bVar1;
  byte bVar2;
  
  DAT_0001 = DAT_0189;
  DAT_0000 = 8 - ((DAT_0189 & 0x38) >> 3);
  bVar2 = 0;
  do {
    DAT_2006 = DAT_0001;
    DAT_2007 = (&DAT_018a)[bVar2];
    DAT_0001 = DAT_0001 + 8;
    bVar2 = bVar2 + 1;
  } while (bVar2 < DAT_0000);
  bVar1 = DAT_0189 & 199;
  do {
    DAT_0001 = bVar1;
    if (7 < bVar2) {
      return;
    }
    DAT_2006 = DAT_0001;
    DAT_2007 = (&DAT_018a)[bVar2];
    bVar2 = bVar2 + 1;
    bVar1 = DAT_0001 + 8;
  } while (bVar2 != 0);
  DAT_0001 = DAT_0001 + 8;
  return;
}



/* 0xf028 FUN_f028 */

void FUN_f028(void)

{
  byte bVar1;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_0000 = 8 - (DAT_019d & 7);
  bVar1 = 0;
  do {
    DAT_2007 = (&DAT_019e)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 < DAT_0000);
  DAT_2006 = DAT_019d & 0xf8;
  do {
    if (7 < bVar1) {
      return;
    }
    DAT_2007 = (&DAT_019e)[bVar1];
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0);
  return;
}



/* 0xf077 FUN_f077 */

void FUN_f077(void)

{
  if (((DAT_009c ^ DAT_009d) & 0xc0) != 0) {
    DAT_0095 = 0xff;
  }
  if (((DAT_009c ^ DAT_009d) & 0x30) != 0) {
    DAT_0094 = 0xff;
  }
  return;
}



/* 0xf206 FUN_f206 */

void FUN_f206(void)

{
  DAT_8000 = DAT_00ae;
  DAT_8800 = DAT_00af;
  DAT_9000 = DAT_00b0;
  DAT_9800 = DAT_00b1;
  bank14_entry_00 = DAT_00b2;
  DAT_a800 = DAT_00b3;
  DAT_b000 = DAT_00b4;
  DAT_b800 = DAT_00b5;
  return;
}



/* 0xf237 FUN_f237 */

undefined1 FUN_f237(undefined1 param_1,byte param_2)

{
  DAT_00e2 = param_2;
  DAT_00e3 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  cRAMf000 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = param_2 | 0xc0;
  return param_1;
}



/* 0xf25f FUN_f25f */

void FUN_f25f(code param_1)

{
  DAT_00e1 = param_1;
  reset_dispatch = param_1;
  return;
}



/* 0xf2af region_address */

void region_address(byte param_1)

{
  DAT_0000 = param_1 * ' ';
  DAT_0001 = (((((param_1 >> 7) << 1 | (param_1 & 0x7f) >> 6) << 1 | (param_1 & 0x3f) >> 5) << 1 |
              (param_1 & 0x1f) >> 4) << 1 | (param_1 & 0xf) >> 3) + 0x60;
  return;
}



/* 0xf2d7 officer_address */

void officer_address(byte param_1)

{
  DAT_0000 = param_1 * '\f' - 0x40;
  DAT_0001 = (((CARRY1(param_1 * '\x02',param_1) - ((char)param_1 >> 7)) * '\x02' |
              (byte)(param_1 * '\x03') >> 7) << 1 | (param_1 * '\x03' & 0x7f) >> 6) + 99 +
             (0x3f < (byte)(param_1 * '\f'));
  return;
}



/* 0xf3bd FUN_f3bd */

void FUN_f3bd(void)

{
  byte bVar1;
  char cVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  DAT_5000 = 0;
  DAT_5800 = 0;
  DAT_c000 = 0xe0;
  DAT_d000 = 0xe0;
  DAT_c800 = 0xe1;
  FUN_d7fb = 0xe1;
  bVar1 = 0;
  do {
    DAT_0001 = (byte)FUN_f3bd[bVar1] & 1;
    DAT_4016 = DAT_0001;
    if (((DAT_4017 >> 1 ^ 0xff) & 1) != DAT_0001) {
      return;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 != 0x46);
  LAB_f800 = 0x40;
  bVar3 = false;
  uStack0000 = 0xf3;
  FUN_f422();
  if (!bVar3) {
    uStack0000 = 0xf4;
    FUN_f43f();
    uStack0000 = 0xf4;
    FUN_f422();
  }
  cVar2 = '\0';
  do {
    cVar2 = cVar2 + '\x01';
  } while (cVar2 != ' ');
  do {
                    /* WARNING: Do nothing block with infinite loop */
  } while( true );
}



/* 0xf422 FUN_f422 */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

char FUN_f422(byte param_1)

{
  char cVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf4;
  FUN_f458();
  do {
    do {
      if (*(char *)(_DAT_0002 + (ushort)param_1) != DAT_0000) {
        return *(char *)(_DAT_0002 + (ushort)param_1);
      }
      uStack0000 = 0xf4;
      FUN_f468();
      param_1 = param_1 + 1;
    } while (param_1 != 0);
    cVar1 = DAT_0003 + '\x01';
    _DAT_0002 = CONCAT11(cVar1,DAT_0002);
  } while (cVar1 != -0x80);
  return '\0';
}



/* 0xf43f FUN_f43f */

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_f43f(byte param_1)

{
  char cVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xf4;
  FUN_f458();
  do {
    do {
      *(undefined1 *)(_DAT_0002 + (ushort)param_1) = DAT_0000;
      uStack0000 = 0xf4;
      FUN_f468();
      param_1 = param_1 + 1;
    } while (param_1 != 0);
    cVar1 = DAT_0003 + '\x01';
    _DAT_0002 = CONCAT11(cVar1,DAT_0002);
  } while (cVar1 != -0x80);
  return;
}



/* 0xf458 FUN_f458 */

void FUN_f458(void)

{
  DAT_0002 = 0;
  DAT_0003 = 0x60;
  DAT_0000 = 0xaa;
  return;
}



/* 0xf468 FUN_f468 */

void FUN_f468(void)

{
  do {
    DAT_0000 = DAT_0000 * '\x05' + '\x01';
  } while (DAT_0000 == '\0');
  return;
}



/* 0xf8af FUN_f8af */

undefined1 FUN_f8af(void)

{
  undefined1 in_stack_00000003;
  
  return in_stack_00000003;
}



/* 0xfa97 switchD_f878::caseD_0 */

undefined1 switchD_f878::caseD_0(void)

{
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
  uStack0000 = 0xfa;
  FUN_fb0b();
  uStack0000 = 0xfa;
  FUN_f206();
  uStack0000 = 0xfa;
  FUN_e6c6();
  uStack0000 = 0xfa;
  FUN_ff62();
  uStack0000 = 0xfa;
  FUN_fb28();
  DAT_007b = DAT_007b + -1;
  reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = bRAM00df | 0xc0;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  uRAMf000 = uRAM00e0;
  cRAM0050 = cRAM0050 + '\x01';
  cRAM0052 = cRAM0052 + '\x01';
  DAT_0054 = DAT_0054 + '\x01';
  cRAM0055 = cRAM0055 + '\x01';
  DAT_005e = DAT_005e + '\x01';
  if (DAT_005e == '\0') {
    DAT_005f = DAT_005f + '\x01';
  }
  return in_stack_00000003;
}



/* 0xfaa9 FUN_faa9 */

void FUN_faa9(void)

{
  undefined1 uVar1;
  undefined1 uVar2;
  
  uVar2 = DAT_0083;
  uVar1 = DAT_0081;
  if (DAT_6f44 != '\0') {
    DAT_0081 = DAT_0082;
    DAT_0082 = uVar1;
    DAT_0083 = DAT_0085;
    DAT_0085 = uVar2;
  }
  return;
}



/* 0xfabf FUN_fabf */

void FUN_fabf(void)

{
  undefined1 uVar1;
  undefined1 uVar2;
  
  uVar2 = DAT_0085;
  uVar1 = DAT_0082;
  if (DAT_6f44 != '\0') {
    DAT_0082 = DAT_0081;
    DAT_0081 = uVar1;
    DAT_0085 = DAT_0083;
    DAT_0083 = uVar2;
  }
  return;
}



/* 0xfad5 FUN_fad5 */

void FUN_fad5(void)

{
  code cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xfa;
  FUN_f206();
  uStack0000 = 0xfa;
  FUN_fb0b();
  bVar2 = DAT_00e2;
  cVar1 = DAT_00e1;
  uStack0000 = DAT_00e3;
  FUN_f237(0x2e);
  thunk_FUN_d8d4();
  LAB_f800 = DAT_00a5;
  reset_dispatch = cVar1;
  bRAMe800 = bVar2 | 0xc0;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  DAT_00e3 = uStack0000;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  uRAMf000 = uStack0000;
  uStack0000 = 0xfb;
  DAT_00e1 = cVar1;
  DAT_00e2 = bVar2;
  FUN_fb28();
  FUN_f8af();
  return;
}



/* 0xfb0b FUN_fb0b */

void FUN_fb0b(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xfb;
  FUN_eaf7();
  DAT_c000 = DAT_00e6;
  DAT_c800 = DAT_00e7;
  DAT_d000 = DAT_00e8;
  FUN_d7fb = DAT_00e9;
  do {
  } while ((DAT_2002 & 0x40) == 0x40);
  return;
}



/* 0xfb28 FUN_fb28 */

void FUN_fb28(void)

{
  do {
  } while (DAT_0062 != '\0');
  return;
}



/* 0xfb2d FUN_fb2d */

undefined1 FUN_fb2d(undefined1 param_1)

{
  byte bVar1;
  char cVar2;
  char cVar3;
  
  if ((DAT_5800 & 0x7f) != 0x7f) {
    do {
                    /* WARNING: Do nothing block with infinite loop */
    } while( true );
  }
  if (DAT_0060 == '\0') {
    DAT_0062 = 0;
    DAT_5000 = 0;
    DAT_5800 = 0;
    return param_1;
  }
  if (DAT_0060 != '\x01') {
    if (DAT_0060 == '\x02') {
      cVar2 = '\b';
      do {
        cVar2 = cVar2 + -1;
      } while (-1 < cVar2);
      bVar1 = (DAT_0099 & 7) << 1;
      DAT_0046 = (&DAT_fd1a)[bVar1];
      DAT_0047 = (&DAT_fd1b)[bVar1];
      do {
        DAT_0046 = DAT_0046 + -1;
      } while (DAT_0046 != '\0');
      do {
        DAT_0047 = DAT_0047 + -1;
      } while (DAT_0047 != '\0');
      cVar2 = '\x1b';
      do {
        cVar2 = cVar2 + -1;
      } while (cVar2 != '\0');
      DAT_0046 = 0;
      DAT_0047 = 0;
      DAT_0062 = 0;
      DAT_2005 = DAT_0096;
      DAT_2006 = DAT_009a;
      DAT_5000 = 0;
      DAT_5800 = 0;
      DAT_8000 = DAT_00b6;
      DAT_8800 = DAT_00b7;
      DAT_9000 = DAT_00b8;
      DAT_9800 = DAT_00b9;
      bank14_entry_00 = DAT_00ba;
      DAT_a800 = DAT_00bb;
      DAT_b000 = DAT_00bc;
      DAT_b800 = DAT_00bd;
      DAT_c700 = DAT_00ea;
      return param_1;
    }
    if (DAT_0060 != '\x03') {
      cVar2 = DAT_0072;
      if (DAT_0060 == '\x04') {
        do {
          cVar2 = cVar2 + -1;
          cVar3 = DAT_0073;
        } while (-1 < cVar2);
        do {
          cVar3 = cVar3 + -1;
          cVar2 = DAT_0074;
        } while (-1 < cVar3);
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = DAT_0096;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        bank14_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c700 = DAT_00ea;
        return param_1;
      }
      if (DAT_0060 == '\x05') {
LAB_fd95:
        cVar2 = '0';
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = DAT_0096;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        bank14_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c700 = 0xe1;
        DAT_c800 = 0xe1;
        DAT_d000 = 0xe1;
        FUN_d7fb = 0xe1;
        return param_1;
      }
      if (DAT_0060 == '\x06') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        return param_1;
      }
      if (DAT_0060 == '\a') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') {
          DAT_c700 = 0xe1;
          DAT_d000 = 0xe1;
          DAT_c800 = 0xe1;
          FUN_d7fb = 0xe1;
          DAT_2006 = 0xb8;
          DAT_2005 = 0;
          goto LAB_fbce;
        }
        if (DAT_0063 == '\x01') goto LAB_fbfc;
        if (DAT_0063 != '\x02') {
          DAT_0063 = '\0';
          goto LAB_fd95;
        }
        goto LAB_fc2a;
      }
      if (DAT_0060 == '\b') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') goto LAB_fbce;
        if (DAT_0063 == '\x01') goto LAB_fbfc;
        if (DAT_0063 == '\x02') goto LAB_fc2a;
        goto LAB_fc58;
      }
      if (DAT_0060 == '\t') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        bank14_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        return param_1;
      }
      if (DAT_0060 == '\n') {
        cVar2 = '\x10';
        do {
          cVar2 = cVar2 + -1;
        } while (-1 < cVar2);
        DAT_0062 = 0;
        DAT_2005 = 0;
        DAT_2006 = DAT_009a;
        DAT_5000 = 0;
        DAT_5800 = 0;
        DAT_8000 = DAT_00b6;
        DAT_8800 = DAT_00b7;
        DAT_9000 = DAT_00b8;
        DAT_9800 = DAT_00b9;
        bank14_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        DAT_b800 = DAT_00bd;
        DAT_c000 = DAT_00ea;
        return param_1;
      }
      if (DAT_0060 == '\v') {
        DAT_5000 = DAT_006a;
        DAT_5800 = DAT_006b;
        DAT_0060 = '\f';
        goto LAB_fbce;
      }
      if (DAT_0060 != '\f') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        return param_1;
      }
      DAT_5000 = DAT_006c;
      DAT_5800 = DAT_006d;
      DAT_0060 = '\n';
      goto LAB_fbfc;
    }
  }
  DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
  DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
  if (DAT_0063 == '\0') {
LAB_fbce:
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00be;
    DAT_8800 = DAT_00bf;
    DAT_9000 = DAT_00c0;
    DAT_9800 = DAT_00c1;
    bank14_entry_00 = DAT_00c2;
    DAT_a800 = DAT_00c3;
    DAT_b000 = DAT_00c4;
    DAT_b800 = DAT_00c5;
    return param_1;
  }
  if (DAT_0063 != '\x01') {
    if (DAT_0063 != '\x02') {
LAB_fc58:
      DAT_0060 = DAT_0060 + '\x01';
      DAT_0063 = 0;
      DAT_8000 = DAT_00d6;
      DAT_8800 = DAT_00d7;
      DAT_9000 = DAT_00d8;
      DAT_9800 = DAT_00d9;
      bank14_entry_00 = DAT_00da;
      DAT_a800 = DAT_00db;
      DAT_b000 = DAT_00dc;
      DAT_b800 = DAT_00dd;
      return param_1;
    }
LAB_fc2a:
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00ce;
    DAT_8800 = DAT_00cf;
    DAT_9000 = DAT_00d0;
    DAT_9800 = DAT_00d1;
    bank14_entry_00 = DAT_00d2;
    DAT_a800 = DAT_00d3;
    DAT_b000 = DAT_00d4;
    DAT_b800 = DAT_00d5;
    return param_1;
  }
LAB_fbfc:
  DAT_b800 = DAT_00cd;
  DAT_b000 = DAT_00cc;
  DAT_a800 = DAT_00cb;
  bank14_entry_00 = DAT_00ca;
  DAT_9800 = DAT_00c9;
  DAT_9000 = DAT_00c8;
  DAT_8800 = DAT_00c7;
  DAT_8000 = DAT_00c6;
  DAT_0063 = DAT_0063 + '\x01';
  return param_1;
}



/* 0xff62 FUN_ff62 */

void FUN_ff62(void)

{
  DAT_0099 = DAT_0098;
  DAT_0047 = (DAT_0098 >> 7) << 1 | (DAT_0098 & 0x78) >> 6;
  DAT_009a = (DAT_0098 & 0xf8) << 2;
  DAT_009b = DAT_0047 + 0x20;
  DAT_00ea = 0xe0;
  DAT_00ec = 0xe0;
  if ((DAT_0097 & 1) != 0) {
    DAT_00ea = 0xe1;
    DAT_00ec = 0xe1;
  }
  return;
}



/* 0xff9b FUN_ff9b */

void FUN_ff9b(void)

{
  DAT_0099 = DAT_0098;
  DAT_0047 = (DAT_0098 >> 7) << 1 | (DAT_0098 & 0x78) >> 6;
  DAT_009a = (DAT_0098 & 0xf8) << 2;
  DAT_009b = DAT_0047 + 0x20;
  DAT_00ea = 0xe0;
  if ((DAT_0097 & 1) != 0) {
    DAT_009b = DAT_0047 + 0x24;
    DAT_00ea = 0xe1;
  }
  return;
}


