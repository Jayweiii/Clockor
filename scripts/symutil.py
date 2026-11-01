"""Extract and resolve KiCad symbols (including extends) for embedding in schematics."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

KICAD_SYM = Path("/workspace/tools/kicad/squashfs-root/usr/share/kicad/symbols")
EXTRA_SYM = Path("/workspace/clockor/hardware/libs")

# Explicit overrides when the same short name could be ambiguous
LIB_OVERRIDE = {
    "DRV8313": "Clockor",
    "ESP32-S3-WROOM-1": "Espressif",
    "ESP32-C3-MINI-1": "Espressif",
}

def _extract(text: str, name: str) -> Optional[str]:
    for m in re.finditer(rf'\(symbol "{re.escape(name)}"[\s\n]', text):
        start = m.start()
        i, depth = start, 0
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            i += 1
    return None

def _find_in_libs(name: str) -> tuple[Optional[Path], Optional[str]]:
    search = list(EXTRA_SYM.glob("*.kicad_sym")) + sorted(KICAD_SYM.glob("*.kicad_sym"))
    for p in search:
        text = p.read_text(errors="ignore")
        block = _extract(text, name)
        if block:
            return p, block
    return None, None

def find_lib(name: str) -> str:
    if name in LIB_OVERRIDE:
        return LIB_OVERRIDE[name]
    path, _ = _find_in_libs(name)
    if not path:
        raise KeyError(f"Symbol not found: {name}")
    return path.stem

def lib_id(name: str) -> str:
    return f"{find_lib(name)}:{name}"

def _extends_of(block: str) -> Optional[str]:
    m = re.search(r'\(extends "([^"]+)"\)', block)
    return m.group(1) if m else None

def resolve_symbol(name: str) -> str:
    """Return a fully resolved lib_symbols entry (no extends), top-level named Lib:Name.

    Sub-units keep the bare Name_U_G form (KiCad 9 schematic embedding rule).
    """
    path, block = _find_in_libs(name)
    if not block:
        raise KeyError(f"Symbol not found: {name}")
    lib = LIB_OVERRIDE.get(name, path.stem)
    chain = [name]
    parent = _extends_of(block)
    props_override = block
    base_block = block
    while parent:
        chain.append(parent)
        _, pblock = _find_in_libs(parent)
        if not pblock:
            raise KeyError(f"Parent symbol {parent} of {name} not found")
        if _extends_of(pblock):
            parent = _extends_of(pblock)
            props_override = pblock
            continue
        base_block = pblock
        break
    if _extends_of(base_block):
        raise RuntimeError(f"Unresolved extends for {name}: {chain}")

    if len(chain) == 1:
        resolved = base_block
        # Ensure top-level / subunits use `name` (already do)
        bare = name
    else:
        base_name = chain[-1]
        leaf = props_override
        resolved = base_block
        # Rename base -> leaf name for top-level AND subunits (extends merge)
        resolved = resolved.replace(f'(symbol "{base_name}"', f'(symbol "{name}"', 1)
        resolved = re.sub(
            rf'\(symbol "{re.escape(base_name)}_(\d+)_(\d+)"',
            rf'(symbol "{name}_\1_\2"',
            resolved,
        )
        for prop in ("Footprint", "Datasheet", "Description", "ki_keywords", "ki_fp_filters", "Value"):
            m = re.search(rf'\(property "{prop}" "([^"]*)"', leaf)
            if m:
                val = m.group(1)
                resolved = re.sub(
                    rf'\(property "{prop}" "[^"]*"',
                    f'(property "{prop}" "{val}"',
                    resolved,
                    count=1,
                )
        resolved = re.sub(
            rf'\(property "Value" "[^"]*"',
            f'(property "Value" "{name}"',
            resolved,
            count=1,
        )
        bare = name

    # Prefix ONLY the top-level symbol with Lib:
    resolved = re.sub(
        rf'^\(symbol "{re.escape(bare)}"',
        f'(symbol "{lib}:{bare}"',
        resolved,
        count=1,
    )
    # Ensure exclude_from_sim / in_bom / on_board exist (KiCad 9)
    if "(in_bom" not in resolved:
        resolved = resolved.replace(
            f'(symbol "{lib}:{bare}"',
            f'(symbol "{lib}:{bare}"\n\t\t(exclude_from_sim no)\n\t\t(in_bom yes)\n\t\t(on_board yes)',
            1,
        )
    # Ensure embedded_fonts no on the symbol
    if "(embedded_fonts" not in resolved:
        resolved = resolved.rstrip()
        if resolved.endswith(")"):
            resolved = resolved[:-1] + "\t(embedded_fonts no)\n\t)"
    # KiCad 9 schematic embedding rejects some symbol-lib-only tokens from newer libs
    resolved = _sanitize_for_sch(resolved)
    return resolved

def _sanitize_for_sch(block: str) -> str:
    """Strip tokens that cause 'Failed to load schematic' when embedded."""
    for tok in [
        r'\(show_name (yes|no)\)\s*',
        r'\(do_not_autoplace (yes|no)\)\s*',
        r'\(in_pos_files (yes|no)\)\s*',
        r'\(duplicate_pin_numbers_are_jumpers (yes|no)\)\s*',
    ]:
        block = re.sub(tok, '', block)
    # Move sibling (hide yes) before (effects ...) into effects
    block = re.sub(
        r'\(hide yes\)\s*\(effects\s*',
        '(effects\n\t\t\t\t(hide yes)\n\t\t\t\t',
        block,
    )
    return block

def pin_numbers(resolved_block: str) -> list[str]:
    pins = re.findall(r'\(number "([^"]+)"', resolved_block)
    seen, out = set(), []
    for p in pins:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

def unit_count(resolved_block: str, name: str) -> int:
    # subunits are bare Name_U_G
    units = re.findall(rf'\(symbol "{re.escape(name)}_(\d+)_\d+"', resolved_block)
    return max((int(u) for u in units), default=1)

if __name__ == "__main__":
    for n in ["ESP32-S3-WROOM-1", "TCA9548APWR", "XL4015", "AMS1117-3.3", "74AHCT125",
              "ME6211C33M5", "APA102-2020", "USB_C_Receptacle_USB2.0_16P", "ESP32-C3-MINI-1",
              "R", "C", "LED", "D", "L", "GND", "+3V3", "+5V", "PWR_FLAG",
              "Conn_01x04", "Barrel_Jack", "SW_Push", "DRV8313", "C_Polarized"]:
        try:
            b = resolve_symbol(n)
            names = re.findall(r'\(symbol "([^"]+)"', b)
            print(f"OK {lib_id(n):50} top={names[0]:40} pins={len(pin_numbers(b))} units={unit_count(b,n)} subs={names[1:4]}")
        except Exception as e:
            print(f"FAIL {n}: {e}")
