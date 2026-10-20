# Audio reconstruction working notes

Original ROM remains read-only. Task scope: reset/sequence requests and actual
logical2E pair14/15 A003 -> bank15 D8D4 tick driver, not waveform/PCM synthesis.
E6C6 is controller4016/4017 sampling; E70E is palette2007 upload, not audio.

- Fixed31 E57F calls request0 atE673, E590 hardware reset, A5/F800=4C.
- E590:4015=0,07F6=0,4000/4004/400C=10,4001/4005=8,4008=0,07F2=0;
 11 slots at0700+22*i:offset0=FF,offset6=0. N163 F800=C0 then64 zeros4800;
 F800=80 then32-byte wave tableE6A6; F800 addresses64/6C/74/7C valueF0;
 final F800=7F,4800=30. No oscillator/audio playback code.
- E609 usesF25F selector22 -> physical2 data window. Descriptor table8000 has
 183 four-byte entries (first stream82DC). Descriptor fields slotOffset,
 logicalchannelType,streamLow,streamHighMinus40. Existing same-slot APU type<4
 is disabled in07F6/4015, then offsets1..3 replaced andoffset0=0. F0/F1 end
 descriptor pointer. E66B/E673/E67B/E683/E68B/E693/E69B load8/7/6/5/4/3/2
 consecutive IDs respectively; E609 loadsone. Original X restored, Y=3,
 finalA=X and flagsNZ fromX,V from descriptorhigh+40,C sameADC.
- Driver D8D4 explicitly mapsE1=22/E00022,E2=23/E800E3. Reset07F2 mask,
 increment07F9.11 priority slots.07F3=type&7,07F5=channel*4,07F4=DD56 flags.
 ActiveFF skip. State0 header initializes0704/5 tempo low4,0706/7 waveform+
 volume,0709 sweep, clears0A/0B/0C/0F, setsstate2, thenparse.
- Active:priority-guarded vibratoDCD8,elapsed0E++ capped0D,tempo05--signed;
 whenunderflow reset low4tempo,volume slideDC90,delay15--nonzero,duration08--;
 zero duration entersD99B parser, otherwise control/envelope DF6E.
- D99B streams TWO-BYTE commands; statebyte countswords. FD stores loopindex,
 FF ends/silences, D/E signed volume slide +period, C envelope/mode,
 B loop counters070A/B, A0 volume,A1 sweep,A2 waveform,A3 vibrato/gatedelay,
 A4 clearschannelhighflags,AD relative streambase/header switch,AE tempo bit7,
 AF low4tempo. Lower A commands unrecognized continue (no fallback).
- Notes0..9F: duration08=param; noise flag40 acceptsnote<10, otherwise rest.
 pitchlow4<12 usesDD06 period words, tempo bit7 selectssecond24B set,
 N163 channel>=4 selects48B offset. Original N163 octaveSBC30 uses carry
 fromCMP40 (borrow foroctave<40), notes>=50 capshift5. periodLow emittedraw,
0712 cache alone clamps2..FD forvibrato.070E=0,0706=baseline07 beforepriority.
- DC31 priority collision pops its ownreturn pluscallerreturn; highlevel means
 suppress currenthelper output. Already updated channel state is retained.
- DCD8 optionally writes4002+channel*4 with0712+DD5E vibrato byphaseF9&0F.
- DC59 envelope performs FOUR 8-bit doubled quotient iterations, CMP loses
 ASL carry, stores quotient bits in07F7. DDCE curve ORvolume indexesDE6E.
- DF87 APU4000+y or N163(pointer((y*2)|67),volume(low4|30),pointer--,
 waveoffset((A&C0)>>3)); DC03/18 writeAPU4002/3 or N163pointer((y*2)|60/62).
 Triangle flag80 directly writes4000+y unchanged andskips envelope/slide.
- ActualcodeD8D4..DD06, tablesDD06..DF6E, outputhelperDF6E..DFBF.
 Finalfulltick A=F2,X=DC,Y=lastslotlogicaltype&7,P(NVZC)=0011,SPunchanged.
 FreeCPUstack residual writes excluded from semanticRAM; caller frame preserved.
 Reset finalA4C,X7F,Y3,V1,N/Z/C0,SPunchanged. Optional register contract may
 expose these end registers; no source6502 executor or original fallback.
- AD nonzero parameter preserves original quirk:sets00F1=0 thenROL statehi,
 updatesstreambase but doesnotreplace00F0/F1 withnewbase beforecontinuing;
 parser reads current actual pointer, includingRAM ifthat path selectsit.
