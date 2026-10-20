
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
    uRAMb800 = 0;
    uRAMd000 = 7;
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
                    /* WARNING: Read-only address (RAM,0xb800) is written */
      do {
        DAT_0046 = DAT_0046 + -1;
      } while (DAT_0046 != '\0');
      do {
        DAT_0047 = DAT_0047 + -1;
      } while (DAT_0047 != '\0');
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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
      bank25_entry_00 = DAT_00ba;
      DAT_a800 = DAT_00bb;
      DAT_b000 = DAT_00bc;
      uRAMb800 = DAT_00bd;
      DAT_c700 = DAT_00ea;
      uRAMd000 = 7;
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
        bank25_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        uRAMb800 = DAT_00bd;
        DAT_c700 = DAT_00ea;
        uRAMd000 = 7;
        return param_1;
      }
      if (DAT_0060 == '\x05') {
LAB_fd95:
                    /* WARNING: Read-only address (RAM,0xd000) is written */
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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
        bank25_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        uRAMb800 = DAT_00bd;
        DAT_c700 = 0xe1;
        DAT_c800 = 0xe1;
        uRAMd000 = 0xe1;
        DAT_d800 = 0xe1;
        return param_1;
      }
      if (DAT_0060 == '\x06') {
        DAT_0062 = 0;
        DAT_5000 = 0;
        DAT_5800 = 0;
        uRAMb800 = 0;
        uRAMd000 = 7;
        return param_1;
      }
      if (DAT_0060 == '\a') {
        DAT_5000 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6a);
        DAT_5800 = *(undefined1 *)((byte)(DAT_0063 << 1) + 0x6b);
        if (DAT_0063 == '\0') {
          DAT_c700 = 0xe1;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
          uRAMd000 = 0xe1;
          DAT_c800 = 0xe1;
          DAT_d800 = 0xe1;
          DAT_2006 = 0xb8;
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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
        bank25_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        uRAMb800 = DAT_00bd;
        uRAMd000 = 7;
        return param_1;
      }
      if (DAT_0060 == '\n') {
                    /* WARNING: Read-only address (RAM,0xb800) is written */
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
        bank25_entry_00 = DAT_00ba;
        DAT_a800 = DAT_00bb;
        DAT_b000 = DAT_00bc;
        uRAMb800 = DAT_00bd;
        DAT_c000 = DAT_00ea;
        uRAMd000 = 7;
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
        uRAMb800 = 0;
        uRAMd000 = 7;
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
                    /* WARNING: Read-only address (RAM,0xb800) is written */
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00be;
    DAT_8800 = DAT_00bf;
    DAT_9000 = DAT_00c0;
    DAT_9800 = DAT_00c1;
    bank25_entry_00 = DAT_00c2;
    DAT_a800 = DAT_00c3;
    DAT_b000 = DAT_00c4;
    uRAMb800 = DAT_00c5;
    return param_1;
  }
  if (DAT_0063 != '\x01') {
    if (DAT_0063 != '\x02') {
LAB_fc58:
                    /* WARNING: Read-only address (RAM,0xb800) is written */
      DAT_0060 = DAT_0060 + '\x01';
      DAT_0063 = 0;
      DAT_8000 = DAT_00d6;
      DAT_8800 = DAT_00d7;
      DAT_9000 = DAT_00d8;
      DAT_9800 = DAT_00d9;
      bank25_entry_00 = DAT_00da;
      DAT_a800 = DAT_00db;
      DAT_b000 = DAT_00dc;
      uRAMb800 = DAT_00dd;
      uRAMd000 = 7;
      return param_1;
    }
LAB_fc2a:
                    /* WARNING: Read-only address (RAM,0xb800) is written */
    DAT_0063 = DAT_0063 + '\x01';
    DAT_8000 = DAT_00ce;
    DAT_8800 = DAT_00cf;
    DAT_9000 = DAT_00d0;
    DAT_9800 = DAT_00d1;
    bank25_entry_00 = DAT_00d2;
    DAT_a800 = DAT_00d3;
    DAT_b000 = DAT_00d4;
    uRAMb800 = DAT_00d5;
    uRAMd000 = 7;
    return param_1;
  }
LAB_fbfc:
                    /* WARNING: Read-only address (RAM,0xb800) is written */
  uRAMd000 = 7;
  uRAMb800 = DAT_00cd;
  DAT_b000 = DAT_00cc;
  DAT_a800 = DAT_00cb;
  bank25_entry_00 = DAT_00ca;
  DAT_9800 = DAT_00c9;
  DAT_9000 = DAT_00c8;
  DAT_8800 = DAT_00c7;
  DAT_8000 = DAT_00c6;
  DAT_0063 = DAT_0063 + '\x01';
                    /* WARNING: Read-only address (RAM,0xb800) is written */
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  return param_1;
}

