"""The B-rep print audit for revision 43's P22 against revision 41's."""
import json
import sys
sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
import print_audit_brep as A
import r41_parts as R41
import r43_parts as R43
new, old = R43.p22(), R41.p22()
nf, of = A.face_rows(new), A.face_rows(old)
ns, nc, angles = A.edge_rows(new)
os_, oc, _ = A.edge_rows(old)
rep = {"valid": new.isValid(), "faces": len(new.Faces()), "edges": len(new.Edges()),
       "small_or_thin_faces": A.tag(nf, of), "short_edges": A.tag(ns, os_), "shallow_creases": A.tag(nc, oc)}
for k in ("small_or_thin_faces", "short_edges", "shallow_creases"):
    fresh = [x for x in rep[k] if not x["inherited"]]
    print(k, len(rep[k]), "new:", json.dumps(fresh))
