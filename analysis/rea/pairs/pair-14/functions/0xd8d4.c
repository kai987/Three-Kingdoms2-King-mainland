
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

