#!/usr/bin/env python3
"""Read-only 6502 inspection of the user-supplied iNES ROM (standard library only).

Never writes the ROM. CPU addresses in switched banks require a selected CPU
window; the caller must choose it. Unknown/unofficial opcodes are shown as data.
"""
from pathlib import Path
import argparse
import hashlib
import json
import csv

ROWS = [
"BRK:i ORA:ix ?:i ?:i ?:i ORA:zp ASL:zp ?:i PHP:i ORA:im ASL:a ?:i ?:i ORA:ab ASL:ab ?:i",
"BPL:rel ORA:iy ?:i ?:i ?:i ORA:zpx ASL:zpx ?:i CLC:i ORA:aby ?:i ?:i ?:i ORA:abx ASL:abx ?:i",
"JSR:ab AND:ix ?:i ?:i BIT:zp AND:zp ROL:zp ?:i PLP:i AND:im ROL:a ?:i BIT:ab AND:ab ROL:ab ?:i",
"BMI:rel AND:iy ?:i ?:i ?:i AND:zpx ROL:zpx ?:i SEC:i AND:aby ?:i ?:i ?:i AND:abx ROL:abx ?:i",
"RTI:i EOR:ix ?:i ?:i ?:i EOR:zp LSR:zp ?:i PHA:i EOR:im LSR:a ?:i JMP:ab EOR:ab LSR:ab ?:i",
"BVC:rel EOR:iy ?:i ?:i ?:i EOR:zpx LSR:zpx ?:i CLI:i EOR:aby ?:i ?:i ?:i EOR:abx LSR:abx ?:i",
"RTS:i ADC:ix ?:i ?:i ?:i ADC:zp ROR:zp ?:i PLA:i ADC:im ROR:a ?:i JMP:ind ADC:ab ROR:ab ?:i",
"BVS:rel ADC:iy ?:i ?:i ?:i ADC:zpx ROR:zpx ?:i SEI:i ADC:aby ?:i ?:i ?:i ADC:abx ROR:abx ?:i",
"?:i STA:ix ?:i ?:i STY:zp STA:zp STX:zp ?:i DEY:i ?:i TXA:i ?:i STY:ab STA:ab STX:ab ?:i",
"BCC:rel STA:iy ?:i ?:i STY:zpx STA:zpx STX:zpy ?:i TYA:i STA:aby TXS:i ?:i ?:i STA:abx ?:i ?:i",
"LDY:im LDA:ix LDX:im ?:i LDY:zp LDA:zp LDX:zp ?:i TAY:i LDA:im TAX:i ?:i LDY:ab LDA:ab LDX:ab ?:i",
"BCS:rel LDA:iy ?:i ?:i LDY:zpx LDA:zpx LDX:zpy ?:i CLV:i LDA:aby TSX:i ?:i LDY:abx LDA:abx LDX:aby ?:i",
"CPY:im CMP:ix ?:i ?:i CPY:zp CMP:zp DEC:zp ?:i INY:i CMP:im DEX:i ?:i CPY:ab CMP:ab DEC:ab ?:i",
"BNE:rel CMP:iy ?:i ?:i ?:i CMP:zpx DEC:zpx ?:i CLD:i CMP:aby ?:i ?:i ?:i CMP:abx DEC:abx ?:i",
"CPX:im SBC:ix ?:i ?:i CPX:zp SBC:zp INC:zp ?:i INX:i SBC:im NOP:i ?:i CPX:ab SBC:ab INC:ab ?:i",
"BEQ:rel SBC:iy ?:i ?:i ?:i SBC:zpx INC:zpx ?:i SED:i SBC:aby ?:i ?:i ?:i SBC:abx INC:abx ?:i",
]
OPS = [x.split(":") for r in ROWS for x in r.split()]
SIZES = {"i":1,"a":1,"im":2,"zp":2,"zpx":2,"zpy":2,"ix":2,"iy":2,"rel":2,"ab":3,"abx":3,"aby":3,"ind":3}

def instruction(data, offset, address):
    op, mode = OPS[data[offset]]
    size = SIZES[mode]
    raw = data[offset:offset+size]
    val = int.from_bytes(raw[1:], "little")
    operand = ""
    if mode == "a": operand = "A"
    elif mode == "im": operand = f"#${val:02X}"
    elif mode == "rel": operand = f"${(address+2+(val if val<128 else val-256))&65535:04X}"
    elif mode in ("zp", "ab"): operand = f"${val:02X}" if mode=="zp" else f"${val:04X}"
    elif mode in ("zpx", "zpy", "abx", "aby"): operand = f"${val:02X}" if mode.startswith("zp") else f"${val:04X}"; operand += ","+mode[-1].upper()
    elif mode == "ix": operand = f"(${val:02X},X)"
    elif mode == "iy": operand = f"(${val:02X}),Y"
    elif mode == "ind": operand = f"(${val:04X})"
    if op == "?": operand=f"${raw[0]:02X}"; op=".byte"
    return size, f"{op:<4} {operand}".rstrip()

def disassemble(data, bank, cpu, start, end):
    bankoff=16+bank*8192
    address=start
    lines=[]
    while address<end:
        offset=bankoff+(address-cpu)
        size, text=instruction(data,offset,address)
        raw=data[offset:offset+size]
        lines.append(f"{offset:06X}  b{bank:02d}:${address:04X}  {raw.hex(' ').upper():<8}  {text}")
        address+=size
    return "\n".join(lines)+"\n"

def extract_tables(data, out):
    """Extract only tables whose addressing/size is supported by ROM code."""
    out.mkdir(parents=True, exist_ok=True)
    def record(base, stride, i, ram_base):
        offset=base+stride*i; raw=data[offset:offset+stride]
        return {"id":i,"rom_offset":f"0x{offset:06X}","cpu_address_in_8000_window":f"0x{0x8000+(offset-16)%8192:04X}","runtime_ram_address":f"0x{ram_base+stride*i:04X}","raw_hex":raw.hex(" ").upper(),"bytes":list(raw)}
    cities=[record(0x20c10,32,i,0x6000) for i in range(30)]
    units=[record(0x22010,12,i,0x63c0) for i in range(237)]
    extra=[record(0x22010,12,i,0x63c0) for i in range(237,240)]
    names=[]
    for i in range(237):
        offset=0x22dc4+13*i; raw=data[offset:offset+13]
        tiles=[]
        for j,t in enumerate(raw[1:]):
            if t==255: break
            fileoff=0x40010+raw[0]*1024+t*16
            tiles.append({"index":j,"tile_in_1k_page":t,"chr_rom_offset":f"0x{fileoff:06X}","x":16*(j//4)+8*(j%2),"y":8*((j%4)//2),"raw_hex":data[fileoff:fileoff+16].hex(" ").upper()})
        name={"id":i,"rom_offset":f"0x{offset:06X}","cpu_address_in_8000_window":f"0x{0x8db4+13*i:04X}","raw_hex":raw.hex(" ").upper(),"chr_1k_bank":raw[0],"tile_indices":list(raw[1:]),"tiles":tiles,"unicode_name":None,"confidence":"high for pixel layout; text transcription not supplied"}
        names.append(name); units[i]["name_glyph_record"]=name
    state=[]
    for i in range(15):
        offset=0x3e08c+2*i; raw=data[offset:offset+2]
        state.append({"state":i,"rom_offset":f"0x{offset:06X}","cpu_address":f"0x{0xe07c+2*i:04X}","raw_hex":raw.hex(" ").upper(),"target_cpu_address":f"0x{int.from_bytes(raw,'little'):04X}","confidence":"high for pointer bytes; state meaning unknown"})
    payload={"rom_sha256":hashlib.sha256(data).hexdigest(),"addressing_note":"CPU $8000 addresses are valid only with physical PRG bank16 (city initial data) or17 (unit initial/name data) selected; written register $30/$31 aliases to bank16/17 on this 256 KiB ROM.","first_table":{"candidate_semantics":"city/province records; exact field labels pending dynamic/visual confirmation","confidence":"high for size/offset/copy; medium for city semantics","rom_offset":"0x020C10","bank":16,"cpu_base":"0x8C00","ram_base":"0x6000","record_size":32,"record_count":30,"records":cities},"second_table":{"candidate_semantics":"officer/general records; exact field labels pending dynamic/visual confirmation","confidence":"high for size/offset/count/copy; medium for general semantics","rom_offset":"0x022010","bank":17,"cpu_base":"0x8000","ram_base":"0x63C0","record_size":12,"record_count":237,"copy_size":2880,"records":units,"three_extra_copied_slots_are_adjacent_pointer_data":extra},"name_glyph_records":names,"reset_state_pointer_table":state,"rng_table":{"cpu_address":"0xE8BA","rom_offset":"0x03E8CA","raw_hex":data[0x3e8ca:0x3e9ca].hex(" ").upper(),"values":list(data[0x3e8ca:0x3e9ca])}}
    (out/"recovered_tables.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    for filename, records,stride in [("city_records_raw.csv",cities,32),("general_records_raw.csv",units,12),("copied_extra_slots.csv",extra,12)]:
        with (out/filename).open("w",newline="") as f:
            columns=["id","rom_offset","cpu_address_in_8000_window","runtime_ram_address","raw_hex"]+[f"byte_{j:02d}" for j in range(stride)]
            if stride==12: columns += ["u16_at_06","u16_at_08","byte_11_low2","byte_11_mid2","byte_11_high4"]
            else: columns += [f"u16_at_{j:02d}" for j in (2,4,6,8,12,14)]
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
            for r in records:
                row={k:r[k] for k in columns if k in r}; raw=r["bytes"]
                row.update({f"byte_{j:02d}":v for j,v in enumerate(raw)})
                if stride==12: row.update(u16_at_06=raw[6]+256*raw[7],u16_at_08=raw[8]+256*raw[9],byte_11_low2=raw[11]&3,byte_11_mid2=(raw[11]>>2)&3,byte_11_high4=raw[11]>>4)
                else: row.update({f"u16_at_{j:02d}":raw[j]+256*raw[j+1] for j in (2,4,6,8,12,14)})
                w.writerow(row)
    with (out/"name_glyph_records.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["id","rom_offset","cpu_address","chr_1k_bank","raw_hex"]+[f"tile_{j:02d}" for j in range(12)])
        for r in names:w.writerow([r["id"],r["rom_offset"],r["cpu_address_in_8000_window"],r["chr_1k_bank"],r["raw_hex"],*r["tile_indices"]])
    with (out/"rng_permutation.csv").open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["index","rom_offset","cpu_address","value","hex"])
        for i,v in enumerate(data[0x3e8ca:0x3e9ca]):w.writerow([i,f"0x{0x3e8ca+i:06X}",f"0x{0xe8ba+i:04X}",v,f"{v:02X}"])
    print(f"Wrote 30 city candidates, 237 general candidates, 3 extra copied slots, 237 glyph records, and RNG table to {out}")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("rom", type=Path)
    p.add_argument("--bank",type=int,default=31)
    p.add_argument("--cpu",type=lambda x:int(x,0),default=0xe000)
    p.add_argument("--start",type=lambda x:int(x,0))
    p.add_argument("--end",type=lambda x:int(x,0))
    p.add_argument("--output",type=Path)
    p.add_argument("--extract-tables",type=Path,help="Write supported table evidence to this directory and exit")
    a=p.parse_args(); data=a.rom.read_bytes()
    if data[:4]!=b"NES\x1a": raise ValueError("Not iNES")
    if a.extract_tables:
        if len(data)!=524304 or hashlib.sha256(data).hexdigest()!="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82":
            raise ValueError("Table extraction addresses apply only to the analyzed ROM SHA256")
        extract_tables(data,a.extract_tables);return
    if a.bank<0 or a.bank>=data[4]*2: raise ValueError("Invalid PRG bank")
    start=a.start if a.start is not None else a.cpu
    end=a.end if a.end is not None else a.cpu+8192
    if not a.cpu<=start<end<=a.cpu+8192: raise ValueError("Range must be in selected CPU window")
    result=disassemble(data,a.bank,a.cpu,start,end)
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(result)
    else: print(result,end="")

if __name__=="__main__": main()
