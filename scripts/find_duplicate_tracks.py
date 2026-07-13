#!/usr/bin/env python3
"""Find duplicate/overlapping copper on a KiCad PCB.

Flags three kinds of redundant routing left behind by manual re-routing:
  1. Exact duplicate segments (identical endpoints, same net/layer)
  2. Overlapping collinear segments (same net/layer, not identical, but one
     run of copper lies on top of another)
  3. Duplicate vias (same location + net)

Usage:
    First generate a full PCB analysis JSON with the kicad-happy skill
    (coordinates are only included with --full):

        python3 <kicad-happy>/skills/kicad/scripts/analyze_pcb.py \\
            board.kicad_pcb --full --output pcb.json

    Then run this script against that JSON:

        python3 find_duplicate_tracks.py pcb.json
        python3 find_duplicate_tracks.py pcb.json --tol 0.02
"""
import argparse
import json
import math
import sys
from collections import defaultdict


def norm_pt(x, y, ndigits=4):
    return (round(x, ndigits), round(y, ndigits))


def collinear_overlap(s1, s2, tol=0.01):
    """True if two same-net/same-layer segments are collinear and their
    spans overlap by more than `tol` mm (independent of exact endpoints)."""
    dx1, dy1 = s1["x2"] - s1["x1"], s1["y2"] - s1["y1"]
    dx2, dy2 = s2["x2"] - s2["x1"], s2["y2"] - s2["y1"]
    len1, len2 = math.hypot(dx1, dy1), math.hypot(dx2, dy2)
    if len1 < 1e-6 or len2 < 1e-6:
        return False

    cross = dx1 * dy2 - dy1 * dx2
    if abs(cross) > tol * len1 * len2:
        return False  # not parallel

    px, py = s2["x1"] - s1["x1"], s2["y1"] - s1["y1"]
    cross2 = dx1 * py - dy1 * px
    if abs(cross2) > tol * len1:
        return False  # not on the same line

    ux, uy = dx1 / len1, dy1 / len1
    t2a = (s2["x1"] - s1["x1"]) * ux + (s2["y1"] - s1["y1"]) * uy
    t2b = (s2["x2"] - s1["x1"]) * ux + (s2["y2"] - s1["y1"]) * uy
    lo2, hi2 = min(t2a, t2b), max(t2a, t2b)
    overlap = min(len1, hi2) - max(0.0, lo2)
    return overlap > tol


def nearest_footprints(fps, x, y, n=3):
    ranked = sorted(fps, key=lambda f: math.hypot(f["x"] - x, f["y"] - y))[:n]
    return [(f["reference"], round(math.hypot(f["x"] - x, f["y"] - y), 2)) for f in ranked]


def midpoint(seg):
    return ((seg["x1"] + seg["x2"]) / 2, (seg["y1"] + seg["y2"]) / 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pcb_json", help="PCB analyzer JSON, generated with analyze_pcb.py --full")
    ap.add_argument("--tol", type=float, default=0.01, help="overlap/parallel tolerance in mm (default 0.01)")
    ap.add_argument("--near", type=int, default=3, help="how many nearest footprints to show per finding (default 3)")
    args = ap.parse_args()

    data = json.load(open(args.pcb_json))

    tracks = data.get("tracks")
    if not tracks or "segments" not in tracks:
        sys.exit(
            "No track segment coordinates found in this JSON. "
            "Re-run analyze_pcb.py with --full so segment x/y data is included."
        )
    segs = tracks["segments"]
    fps = data.get("footprints", [])
    net_name = {v: k for k, v in data.get("net_name_to_id", {}).items()}

    def label(net_id):
        return net_name.get(net_id, f"net#{net_id}")

    # 1. Exact duplicates
    exact = defaultdict(list)
    for i, s in enumerate(segs):
        p1, p2 = norm_pt(s["x1"], s["y1"]), norm_pt(s["x2"], s["y2"])
        key = (s["layer"], s["net"], tuple(sorted([p1, p2])))
        exact[key].append(i)
    exact_dupes = {k: v for k, v in exact.items() if len(v) > 1}

    # 2. Overlapping collinear (excluding pairs already caught as exact dupes)
    exact_pairs = set()
    for idxs in exact_dupes.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                exact_pairs.add((idxs[a], idxs[b]))

    by_net_layer = defaultdict(list)
    for i, s in enumerate(segs):
        by_net_layer[(s["net"], s["layer"])].append(i)

    overlap_pairs = []
    for idxs in by_net_layer.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                if (i, j) in exact_pairs:
                    continue
                if collinear_overlap(segs[i], segs[j], tol=args.tol):
                    overlap_pairs.append((i, j))

    # 3. Duplicate vias
    via_section = data.get("vias")
    via_list = via_section.get("vias") if isinstance(via_section, dict) else via_section
    via_dupes = []
    if isinstance(via_list, list):
        seen = defaultdict(list)
        for i, v in enumerate(via_list):
            key = (round(v.get("x", 0), 4), round(v.get("y", 0), 4), v.get("net"))
            seen[key].append(i)
        via_dupes = [(k, v) for k, v in seen.items() if len(v) > 1]

    print(f"Board: {args.pcb_json}")
    print(f"Total track segments: {len(segs)}")
    print()

    print(f"Exact duplicate segment groups: {len(exact_dupes)}")
    for (layer, net, pts), idxs in exact_dupes.items():
        (x1, y1), (x2, y2) = pts
        near = nearest_footprints(fps, (x1 + x2) / 2, (y1 + y2) / 2, args.near) if fps else []
        print(f"  net={label(net)} layer={layer} ({x1},{y1})-({x2},{y2}) segments={idxs} near={near}")

    print()
    print(f"Overlapping (non-identical) collinear segment pairs: {len(overlap_pairs)}")
    for i, j in overlap_pairs:
        mx, my = midpoint(segs[i])
        near = nearest_footprints(fps, mx, my, args.near) if fps else []
        print(f"  net={label(segs[i]['net'])} layer={segs[i]['layer']} seg[{i}]={segs[i]} <--> seg[{j}]={segs[j]} near={near}")

    print()
    print(f"Duplicate via locations: {len(via_dupes)}")
    for (x, y, net), idxs in via_dupes:
        near = nearest_footprints(fps, x, y, args.near) if fps else []
        print(f"  net={label(net)} at=({x},{y}) vias={idxs} near={near}")

    total = len(exact_dupes) + len(overlap_pairs) + len(via_dupes)
    print()
    if total == 0:
        print("No redundant routing found.")
    else:
        print(f"{total} potential redundant-routing issue(s) found — review in KiCad before ordering.")


if __name__ == "__main__":
    main()
