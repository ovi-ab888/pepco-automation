import json, sys, re
from xml.etree import ElementTree as ET

PAGE_W, PAGE_H = 130.394, 325.984

def load_manifest(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_svg_ids(path):
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"svg": re.match(r"\{.*\}", root.tag).group(0)[1:-1]} if root.tag.startswith("{") else {}
    ids = set()
    for el in root.iter():
        _id = el.attrib.get("id")
        if _id:
            ids.add(_id)
    return ids

def main(svg_path, manifest_path):
    man = load_manifest(manifest_path)
    svg_ids = load_svg_ids(svg_path)

    errors = []
    # 1) fonts block
    if "fonts" not in man or "regular" not in man["fonts"] or "bold" not in man["fonts"]:
        errors.append("fonts.regular / fonts.bold missing")
    # 2) fields coverage + ranges
    mf_ids = set()
    for f in man.get("fields", []):
        fid = f.get("id")
        mf_ids.add(fid)
        if fid not in svg_ids:
            errors.append(f"[MISSING IN SVG] id '{fid}' not found")
        for k in ("x","y","w","h","size"):
            if k not in f:
                errors.append(f"[MISSING KEY] field {fid}: '{k}' absent")
        x,y,w,h = f.get("x",0), f.get("y",0), f.get("w",0), f.get("h",0)
        if not (0 <= x <= PAGE_W and 0 <= y <= PAGE_H):
            errors.append(f"[OUT OF PAGE] {fid}: x/y=({x},{y}) out of 0..{PAGE_W}/{PAGE_H}")
        if w <= 0 or h <= 0:
            errors.append(f"[SIZE<=0] {fid}: w/h=({w},{h})")
        if f.get("font") not in ("regular","bold"):
            errors.append(f"[FONT KEY] {fid}: font='{f.get('font')}' should be 'regular' or 'bold'")

    # 3) svg has extra var_* not in manifest
    extra_vars = {i for i in svg_ids if i.startswith("var_")} - mf_ids
    for eid in sorted(extra_vars):
        errors.append(f"[EXTRA IN SVG] '{eid}' exists in SVG but not in manifest")

    if errors:
        print("❌ Validation failed (" + str(len(errors)) + " issues):")
        for e in errors:
            print(" - " + e)
        sys.exit(1)
    else:
        print("✅ Validation passed: SVG ↔ manifest look consistent.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python backend/scripts/validate_manifest.py <Template.svg> <template_manifest.json>")
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
