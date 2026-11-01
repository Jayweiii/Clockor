#!/usr/bin/env python3
"""Stand-alone connectivity extractor for the generated Clockor schematics.

Why this exists: the schematics are produced by `rebuild_boards.py`, which
attaches net labels to pin tips by coordinate. A label or wire that happens to
land on another pin silently creates a short (that is how USB-C CC1 ended up on
+5V in v0.5). This script recomputes the netlist straight from the
`.kicad_sch` geometry so a regenerated sheet can be checked without KiCad, and
it can assert the intended net map.

Validated against KiCad 9.0.7 `kicad-cli sch export netlist` output for the
v0.5 sheets (see `--compare`).

Usage:
  python3 scripts/sch_netcheck.py hardware/base-controller/base-controller.kicad_sch
  python3 scripts/sch_netcheck.py SCH --compare review/base-controller.net
  python3 scripts/sch_netcheck.py SCH --json out.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------- s-expr parse
def parse_sexpr(text: str):
    tokens = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+', text)
    stack: list[list] = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        elif t.startswith('"'):
            stack[-1].append(t[1:-1].replace('\\"', '"'))
        else:
            stack[-1].append(t)
    return stack[0][0]


def children(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def child(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def prop(node, name):
    for c in children(node, "property"):
        if c[1] == name:
            return c[2]
    return None


# ---------------------------------------------------------------- geometry
def key(x: float, y: float) -> tuple[int, int]:
    # 1 µm grid: generator coordinates are exact decimals in mm
    return (round(x * 1000), round(y * 1000))


def on_segment(p, a, b) -> bool:
    (px, py), (ax, ay), (bx, by) = p, a, b
    if (px - ax) * (by - ay) - (py - ay) * (bx - ax) != 0:
        return False
    return min(ax, bx) <= px <= max(ax, bx) and min(ay, by) <= py <= max(ay, by)


class DSU:
    def __init__(self):
        self.p: dict = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


# ---------------------------------------------------------------- netlist
def lib_pins(lib_sym) -> dict[int, list[tuple[str, str, float, float, bool, str]]]:
    """{unit: [(number, name, x, y, is_power_in_hidden, etype)]}; unit 0 = common."""
    out: dict[int, list] = defaultdict(list)
    for sub in children(lib_sym, "symbol"):
        m = re.search(r"_(\d+)_(\d+)$", sub[1])
        unit = int(m.group(1)) if m else 0
        for pin in children(sub, "pin"):
            at = child(pin, "at")
            num = child(pin, "number")[1]
            name = child(pin, "name")[1]
            hidden = "hide" in [x for x in pin if isinstance(x, str)] or any(
                isinstance(x, list) and x[:2] == ["hide", "yes"] for x in pin
            )
            out[unit].append((num, name, float(at[1]), float(at[2]), pin[1] == "power_in" and hidden, pin[1]))
    return out


def netlist(sch_path: Path):
    root = parse_sexpr(sch_path.read_text())
    libs = {s[1]: s for s in children(child(root, "lib_symbols"), "symbol")}

    dsu = DSU()
    points: list[tuple[int, int]] = []          # every connectable point
    pin_at: dict[tuple[str, str], tuple] = {}  # (ref, pin) -> key
    pin_name: dict[tuple[str, str], str] = {}
    power_names: list[tuple[tuple, str]] = []
    nc_points: set = set()
    pin_type: dict[tuple[str, str], str] = {}
    flag_points: list = []

    for sym in children(root, "symbol"):
        lib_id = child(sym, "lib_id")[1]
        at = child(sym, "at")
        sx, sy, rot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
        unit = int(child(sym, "unit")[1]) if child(sym, "unit") else 1
        ref = prop(sym, "Reference")
        value = prop(sym, "Value")
        mirror = child(sym, "mirror")
        lp = lib_pins(libs[lib_id])
        is_power = child(libs[lib_id], "power") is not None
        th = math.radians(rot)
        for num, name, px, py, pwr_hidden, etype in lp.get(0, []) + lp.get(unit, []):
            if mirror and mirror[1] == "y":
                px = -px
            if mirror and mirror[1] == "x":
                py = -py
            rx = px * math.cos(th) - py * math.sin(th)
            ry = px * math.sin(th) + py * math.cos(th)
            k = key(sx + rx, sy - ry)
            points.append(k)
            dsu.find(k)
            pin_at[(ref, num)] = k
            pin_name[(ref, num)] = name
            pin_type[(ref, num)] = etype
            if value == "PWR_FLAG":
                flag_points.append(k)
            if is_power and pwr_hidden or (is_power and not ref.startswith("#FLG")):
                if value != "PWR_FLAG":
                    power_names.append((k, value))

    wires = []
    for w in children(root, "wire"):
        pts = child(w, "pts")
        (_, x1, y1), (_, x2, y2) = pts[1], pts[2]
        a, b = key(float(x1), float(y1)), key(float(x2), float(y2))
        wires.append((a, b))
        dsu.union(a, b)
        points += [a, b]

    labels: list[tuple[tuple, str]] = []
    for kind in ("label", "global_label", "hierarchical_label"):
        for lab in children(root, kind):
            at = child(lab, "at")
            k = key(float(at[1]), float(at[2]))
            labels.append((k, lab[1]))
            points.append(k)
            dsu.find(k)
    for nc in children(root, "no_connect"):
        at = child(nc, "at")
        nc_points.add(key(float(at[1]), float(at[2])))

    # KiCad rule (matches kicad-cli on the v0.5 sheets): labels connect anywhere
    # along a wire; pins and wire ends lying on another wire's interior connect
    # only where a junction is placed.
    junctions = {key(float(child(j, "at")[1]), float(child(j, "at")[2])) for j in children(root, "junction")}
    wire_ends = {p for w in wires for p in w}
    attach = {k for k, _ in labels}
    for p in attach | ((wire_ends | set(pin_at.values())) & junctions):
        for a, b in wires:
            if p != a and p != b and on_segment(p, a, b):
                dsu.union(p, a)
    self_overlaps = []
    for p in (wire_ends | set(pin_at.values())) - junctions - attach:
        for a, b in wires:
            if p != a and p != b and on_segment(p, a, b):
                self_overlaps.append(p)
    netlist.overlaps = self_overlaps  # pins/wire ends lying on other wires, not joined

    # same-name labels / power symbols are one net
    by_name: dict[str, list] = defaultdict(list)
    for k, name in labels + power_names:
        by_name[name].append(k)
    for name, ks in by_name.items():
        for k in ks[1:]:
            dsu.union(ks[0], k)

    groups: dict = defaultdict(set)
    for (ref, num), k in pin_at.items():
        if ref.startswith("#"):
            continue
        groups[dsu.find(k)].add((ref, num))
    names: dict = defaultdict(set)
    for k, name in labels + power_names:
        names[dsu.find(k)].add(name)

    nets = {}
    for root_k, members in groups.items():
        nm = sorted(names.get(root_k, []))
        if nm:
            label = nm[0] if len(nm) == 1 else "|".join(nm)
        elif len(members) == 1 and pin_at[next(iter(members))] in nc_points:
            label = "NC:" + "-".join(next(iter(members)))
        else:
            label = "UNNAMED:" + ",".join(sorted("-".join(m) for m in members))
        nets.setdefault(label, set()).update(members)
    netlist.info = dict(
        root_of={m: dsu.find(k) for m, k in pin_at.items()},
        groups=groups, names=names, pin_type=pin_type, nc_points=nc_points,
        pin_at=pin_at, flag_roots={dsu.find(k) for k in flag_points},
        label_roots=[(dsu.find(k), n) for k, n in labels],
    )
    return nets, pin_name


# Intentional multi-name nets in the Clockor sheets
DEFAULT_ALIASES = [
    {"GND", "SLIP_GND"}, {"+5V", "SLIP_5V"},
    {"M1_EN_ALL", "M1_EN1", "M1_EN2", "M1_EN3"}, {"M1_nSLEEP", "M1_nRESET"},
]


def check(sch_path: Path, aliases: list[set[str]] | None = None) -> list[str]:
    """ERC-lite: collisions, floating pins, undriven power nets, single-pin nets."""
    aliases = DEFAULT_ALIASES if aliases is None else aliases
    nets, pin_name = netlist(sch_path)
    info = netlist.info
    problems = []
    for root_k, nm in info["names"].items():
        if len(nm) > 1 and not any(nm <= a for a in aliases):
            problems.append(f"SHORT: net carries several names {sorted(nm)}")
    for (ref, num), k in info["pin_at"].items():
        if ref.startswith("#"):
            continue
        members = info["groups"][info["root_of"][(ref, num)]]
        named = info["root_of"][(ref, num)] in info["names"]
        if k in info["nc_points"]:
            if len(members) > 1 or named:
                problems.append(f"COLLISION: no-connect pin {ref}.{num} ({pin_name[(ref, num)]}) touches {sorted('.'.join(m) for m in members)}")
        elif len(members) == 1 and not named and info["pin_type"][(ref, num)] != "no_connect":
            problems.append(f"FLOATING: {ref}.{num} ({pin_name[(ref, num)]}) has no connection and no no-connect flag")
        elif len(members) == 1 and named and info["pin_type"][(ref, num)] not in ("no_connect",):
            problems.append(f"SINGLE: {ref}.{num} ({pin_name[(ref, num)]}) is the only pin on net {sorted(info['names'][info['root_of'][(ref, num)]])}")
    for p in getattr(netlist, "overlaps", []):
        problems.append(f"OVERLAP: pin/wire end at {p[0]/1000:.2f},{p[1]/1000:.2f} mm lies on another wire (not joined — move it)")
    for root_k, members in info["groups"].items():
        types = {info["pin_type"][m] for m in members}
        if "power_in" in types and "power_out" not in types and root_k not in info["flag_roots"]:
            problems.append(f"UNDRIVEN: power_in pins on {sorted(info['names'].get(root_k, ['?']))} with no power_out or PWR_FLAG")
    return problems


def kicad_net_partition(net_path: Path):
    s = net_path.read_text()
    out = {}
    for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)(.*?)(?=\(net \(code|\Z)', s, re.S):
        nodes = set(re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)))
        out[m.group(1)] = nodes
    return out


def compare(ours: dict, theirs: dict) -> list[str]:
    a = {frozenset(v) for v in ours.values() if len(v) > 1}
    b = {frozenset(v) for v in theirs.values() if len(v) > 1}
    diffs = []
    for s in sorted(a - b, key=lambda s: sorted(s)):
        diffs.append("only-here : " + ", ".join(sorted(".".join(x) for x in s)))
    for s in sorted(b - a, key=lambda s: sorted(s)):
        diffs.append("only-kicad: " + ", ".join(sorted(".".join(x) for x in s)))
    return diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sch", type=Path)
    ap.add_argument("--compare", type=Path, help="KiCad .net file to diff against")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--check", action="store_true", help="run ERC-lite collision checks")
    args = ap.parse_args()
    if args.check:
        probs = [p for p in check(args.sch) if not p.startswith("SINGLE")]
        for pr in probs:
            print(pr)
        print(f"{len(probs)} problem(s) in {args.sch}")

    nets, pin_name = netlist(args.sch)
    if not args.quiet:
        for name in sorted(nets):
            members = sorted(nets[name], key=lambda m: (m[0], m[1]))
            print(f"{name}: " + ", ".join(f"{r}.{p}({pin_name[(r, p)]})" for r, p in members))
    if args.json:
        args.json.write_text(json.dumps({k: sorted(".".join(m) for m in v) for k, v in nets.items()}, indent=1))
    if args.compare:
        diffs = compare(nets, kicad_net_partition(args.compare))
        print(f"\ncompare vs {args.compare}: {len(diffs)} differing groups")
        for d in diffs:
            print("  " + d)
        sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
