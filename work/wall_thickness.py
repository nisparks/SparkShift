"""Ray-cast wall thickness: distance from a surface point, straight inward, to the opposite wall.

A hit counts only if the exit face faces away (its outward normal within 60 degrees of the ray), so
rays grazing out through a neighbouring face at an edge or fillet are ignored. Reports area below limits
and 4 mm clusters of thin wall.
"""
import json
import os
import sys

import numpy as np
import trimesh


def thickness(mesh, n=80000, seed=0, offset=0.01):
    pts, fi = trimesh.sample.sample_surface_even(mesh, n, seed=seed)
    nrm = mesh.face_normals[fi]
    origins = pts - nrm * offset
    t = np.full(len(pts), np.inf)
    loc, ri, tri = mesh.ray.intersects_location(origins, -nrm, multiple_hits=True)
    if len(ri):
        d = np.einsum("ij,ij->i", loc - origins[ri], -nrm[ri])
        facing = np.einsum("ij,ij->i", mesh.face_normals[tri], -nrm[ri]) > 0.5
        ok = (d > 0.02) & facing
        for r, dd in zip(ri[ok], d[ok]):
            if dd + offset < t[r]:
                t[r] = dd + offset
    return pts, t


def report(name, mesh, limits=(0.9, 1.2, 1.6, 2.0), cluster_below=1.6, box=None):
    pts, t = thickness(mesh)
    area_per = mesh.area / len(pts)
    if box is not None:
        lo, hi = np.array(box[0]), np.array(box[1])
        keep = np.all((pts >= lo) & (pts <= hi), axis=1)
        pts, t = pts[keep], t[keep]
    out = {"part": name, "sampled_area_mm2": round(len(pts) * area_per, 1)}
    for lim in limits:
        out[f"below_{lim}"] = round(float((t < lim).sum() * area_per), 1)
    sel = t < cluster_below
    clusters = []
    if sel.any():
        p, tt = pts[sel], t[sel]
        used = np.zeros(len(p), bool)
        for i in np.argsort(tt):
            if used[i]:
                continue
            near = (np.linalg.norm(p - p[i], axis=1) < 4.0) & ~used
            used |= near
            clusters.append({"at": [round(float(v), 1) for v in p[near].mean(axis=0)],
                             "min": round(float(tt[near].min()), 2), "area": round(float(near.sum() * area_per), 1)})
    out["clusters"] = sorted(clusters, key=lambda c: (-c["area"]))[:14]
    return out


if __name__ == "__main__":
    rows = []
    for name, path in zip(sys.argv[1::2], sys.argv[2::2]):
        r = report(name, trimesh.load(path, force="mesh"))
        rows.append(r)
        print(json.dumps(r))
