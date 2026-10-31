"""Print-part geometry audit: tiny faces, slivers, short edges, micro-steps and shallow creases (B-rep)."""
import json
import math
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402
from OCP.BRep import BRep_Tool  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE  # noqa: E402
from OCP.TopExp import TopExp  # noqa: E402
from OCP.TopoDS import TopoDS  # noqa: E402
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape  # noqa: E402

import r37_parts as P37  # noqa: E402
import r40_parts as P40  # noqa: E402
import r41_parts as R  # noqa: E402
import r42_parts as R42  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402
from build_modular_toolhead import load  # noqa: E402

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\print_audit_brep.json")
SMALL_FACE_MM2, THIN_FACE_MM, SHORT_EDGE_MM = 0.5, 0.15, 0.1
CREASE_DEG = (0.3, 25.0)


def parts():
    return {
        "P20": (load(R.NAMES["p20"]), load(P40.NAMES["p20"])),
        "P21": (load(R.NAMES["p21"]), load(P40.NAMES["p21"])),
        "P22": (load(R.NAMES["p22"]), load(P37.NAMES["p22"])),
        "P23_Cartographer": (load(R42.NAMES["p23"]), load(P37.NAMES["p23"])),
        "P23_Beacon": (load(P37.NAMES["p23"]), load("P23_Beacon_Cartographer_Mount")),
    }


def r(v, n=3):
    return [round(x, n) for x in v]


def face_rows(s):
    out = []
    for f in s.Faces():
        a = f.Area()
        per = sum(e.Length() for e in f.Edges())
        width = 2 * a / per if per > 0 else 0.0
        if a < SMALL_FACE_MM2 or width < THIN_FACE_MM:
            c = f.Center()
            out.append({"area_mm2": round(a, 4), "width_mm": round(width, 4), "type": f.geomType(),
                        "centre": r((c.x, c.y, c.z)), "bounds": r(bounds(f))})
    return out


def edge_rows(s):
    m = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(s.wrapped, TopAbs_EDGE, TopAbs_FACE, m)
    short, creases, angles = [], [], []
    for i in range(1, m.Extent() + 1):
        e = TopoDS.Edge_s(m.FindKey(i))
        if BRep_Tool.Degenerated_s(e):
            continue
        edge = cq.Edge(e)
        length = edge.Length()
        mid = edge.positionAt(0.5)
        faces = [TopoDS.Face_s(f) for f in m.FindFromIndex(i)]
        uniq = []
        for f in faces:
            if not any(f.IsSame(g) for g in uniq):
                uniq.append(f)
        if length < SHORT_EDGE_MM:
            short.append({"length_mm": round(length, 4), "mid": r((mid.x, mid.y, mid.z)), "faces": len(uniq)})
        if len(uniq) != 2:
            continue
        try:
            n1, n2 = cq.Face(uniq[0]).normalAt(mid), cq.Face(uniq[1]).normalAt(mid)
        except Exception:
            continue
        ang = math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))
        angles.append(ang)
        if CREASE_DEG[0] < ang < CREASE_DEG[1]:
            creases.append({"angle_deg": round(ang, 2), "length_mm": round(length, 3), "mid": r((mid.x, mid.y, mid.z)),
                            "faces": [cq.Face(uniq[0]).geomType(), cq.Face(uniq[1]).geomType()]})
    return short, creases, angles


def key(row):
    return tuple(round(v, 1) for v in row.get("centre", row.get("mid")))


def tag(rows, old_rows):
    old = {key(o) for o in old_rows}
    for row in rows:
        row["inherited"] = key(row) in old
    return rows


def main():
    report = {}
    for name, (new, old) in parts().items():
        nf, of = face_rows(new), face_rows(old)
        ns, nc, angles = edge_rows(new)
        os_, oc, _ = edge_rows(old)
        report[name] = {
            "valid": new.isValid(), "solids": len(new.Solids()), "faces": len(new.Faces()), "edges": len(new.Edges()),
            "volume_mm3": round(new.Volume(), 2),
            "small_or_thin_faces": tag(nf, of), "short_edges": tag(ns, os_), "shallow_creases": tag(nc, oc),
            "dihedral_histogram_deg": {
                "tangent_<0.3": sum(a <= 0.3 for a in angles), "0.3-5": sum(0.3 < a <= 5 for a in angles),
                "5-25": sum(5 < a <= 25 for a in angles), "25-60": sum(25 < a <= 60 for a in angles),
                "60-120": sum(60 < a <= 120 for a in angles), ">120": sum(a > 120 for a in angles)}}
        rep = report[name]
        new_items = lambda k: [x for x in rep[k] if not x["inherited"]]
        print(f"{name}: valid {rep['valid']}, {rep['faces']} faces, {rep['edges']} edges; small/thin faces "
              f"{len(rep['small_or_thin_faces'])} ({len(new_items('small_or_thin_faces'))} new); short edges "
              f"{len(rep['short_edges'])} ({len(new_items('short_edges'))} new); shallow creases "
              f"{len(rep['shallow_creases'])} ({len(new_items('shallow_creases'))} new); dihedral {rep['dihedral_histogram_deg']}",
              flush=True)
    OUT.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
