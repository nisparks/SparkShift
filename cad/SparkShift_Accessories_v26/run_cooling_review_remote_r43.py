"""Run one prepared review case on the user's existing CFD host, verify the download, then clean only that case.

python run_cooling_review_remote_r43.py r43auditRVMS28fine_bambu_bed --host user@host
The image must already exist. No other containers, cases or host configuration are changed.
"""
import argparse
import json
import shlex
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

import cfd_cpap_r41 as C
from cfd_provenance_r43 import digest

REMOTE_RUN = r'''
import hashlib, json, os, re, shutil, subprocess, sys, tarfile
from pathlib import Path, PurePosixPath
name, archive_sha, runner_sha = sys.argv[1:]
if not re.fullmatch(r"r43audit[A-Za-z0-9_]+", name):
    raise SystemExit("Invalid review case")
root = Path.home() / "sparkshift_cfd"
os.chdir(root)
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()
archive, runner = root / (name+".tgz"), root / "run_cooling_review_r43.sh"
if sha(archive) != archive_sha or sha(runner) != runner_sha:
    raise SystemExit("Uploaded input/runner hash mismatch")
case = root / name
if case.exists():
    raise SystemExit("Refusing to overwrite remote case")
active = subprocess.check_output(["docker","ps","--format","{{.Names}}"],text=True).splitlines()
if any(n.startswith("sfcfd_") for n in active):
    raise SystemExit("Another CFD container is running; case was not started")
if shutil.disk_usage(root).free < 5*1024**3:
    raise SystemExit("Insufficient remote free space for this case")
with tarfile.open(archive) as tf:
    for member in tf.getmembers():
        p=PurePosixPath(member.name)
        if p.is_absolute() or ".." in p.parts or p.parts[0] != name or not (member.isfile() or member.isdir()):
            raise SystemExit("Unsafe input archive member")
    tf.extractall(root)
manifest=json.loads((case/"input_hashes.json").read_text())
hash_lines=[]
for filename, expected in manifest.items():
    filename=filename.replace("\\","/")
    p=(case/filename).resolve()
    p.relative_to(case)
    if "\n" in filename or sha(p) != expected:
        raise SystemExit("Extracted case input hash mismatch: "+filename)
    hash_lines.append(expected+"  "+filename+"\n")
(case/"input_hashes.sha256").write_text("".join(hash_lines))
image="opencfd/openfoam-default:2512"
image_id=subprocess.check_output(["docker","image","inspect",image,"--format","{{.Id}}"],text=True).strip()
container="sfcfd_"+name
command=["docker","run","-d","--name",container,"--shm-size=8g","-v",str(root)+":/work",
         "--user",str(os.getuid())+":"+str(os.getgid()),"-e","HOME=/work","--entrypoint","bash",image,
         "/work/run_cooling_review_r43.sh","/work/"+name]
cid=subprocess.check_output(command,text=True).strip()
(case/"run_identity.json").write_text(json.dumps({"image":image,"image_id":image_id,
    "container_id":cid,"input_archive_sha256":archive_sha,"runner_sha256":runner_sha},indent=2))
print(name+" running in "+cid,flush=True)
state=subprocess.check_output(["docker","inspect",container,"--format","{{.State.Status}}"],text=True).strip()
print("Container state: "+state,flush=True)
code=int(subprocess.check_output(["docker","wait",container],text=True).strip())
if code:
    subprocess.run(["docker","logs","--tail","50",container],check=True)
    for log in ["log.run","log.surfaceCheck","log.checkMesh","log.simpleFoam"]:
        p=case/log
        if p.exists():
            print(log+"\n"+"\n".join(p.read_text(errors="replace").splitlines()[-12:]),flush=True)
    raise SystemExit(code)
selected=["VTK","postProcessing","constant/polyMesh","1200","domain.json","stages.json",
          "input_hashes.json","input_hashes.sha256","run_identity.json","runtime.txt"]
selected += sorted(p.name for p in case.glob("log.*") if p.is_file())
files={}
for entry in selected:
    p=case/entry
    for f in (p.rglob("*") if p.is_dir() else [p]):
        if f.is_file():
            files[str(f.relative_to(case))]=sha(f)
(case/"output_hashes.json").write_text(json.dumps(files,indent=2))
(case/"archive_entries.json").write_text(json.dumps(selected+["output_hashes.json","archive_entries.json"]))
print(name+" solved; outputs hashed",flush=True)
'''

REMOTE_TAR = r'''
import json, os, subprocess, sys
from pathlib import Path
name=sys.argv[1]
root=Path.home()/"sparkshift_cfd"
entries=json.loads((root/name/"archive_entries.json").read_text())
os.chdir(root)
subprocess.run(["tar","-czf","-",*[name+"/"+p for p in entries]],check=True)
'''

REMOTE_CLEAN = r'''
import json, re, shutil, subprocess, sys
from pathlib import Path
name, identity_sha=sys.argv[1:]
if not re.fullmatch(r"r43audit[A-Za-z0-9_]+",name):
    raise SystemExit("Invalid cleanup scope")
root=(Path.home()/"sparkshift_cfd").resolve()
case=(root/name).resolve()
if case.parent != root:
    raise SystemExit("Cleanup escaped case directory")
import hashlib
if hashlib.sha256((case/"run_identity.json").read_bytes()).hexdigest() != identity_sha:
    raise SystemExit("Run identity changed before cleanup")
state=subprocess.check_output(["docker","inspect","sfcfd_"+name,"--format","{{.State.Status}} {{.State.ExitCode}}"],
                              text=True).strip()
if state != "exited 0":
    raise SystemExit("Refusing to remove a running or failed case")
subprocess.run(["docker","rm","sfcfd_"+name],check=True)
shutil.rmtree(case)
(root/(name+".tgz")).unlink()
print("Cleaned only verified, downloaded case "+name,flush=True)
'''


def remote(host, code, *args, stdout=None):
    command = "python3 -c " + shlex.quote(code) + " " + " ".join(shlex.quote(a) for a in args)
    result = subprocess.run(["ssh", "-o", "ConnectTimeout=15", host, command], stdout=stdout)
    if result.returncode:
        raise RuntimeError(f"Remote CFD stage failed with exit {result.returncode}; diagnostic output is above")


def run(name, host, collect=False):
    if not name.startswith("r43audit") or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in name):
        raise ValueError("Invalid new review case name")
    destination = C.results_dir(name)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite results {destination}")
    if not collect:
        archive = C.CFD / "cases" / f"{name}.tgz"
        runner = Path(__file__).with_name("run_cooling_review_r43.sh")
        if b"\r" in runner.read_bytes():
            raise ValueError("The Linux runner must use LF line endings")
        subprocess.run(["scp", "-q", str(archive), str(runner), f"{host}:sparkshift_cfd/"], check=True)
        remote(host, REMOTE_RUN, name, digest(archive), digest(runner))
    incoming = C.CFD / "results" / f"{name}_verified_download.tgz"
    with incoming.open("xb") as stream:
        remote(host, REMOTE_TAR, name, stdout=stream)
    with tarfile.open(incoming) as tf:
        for member in tf.getmembers():
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts or p.parts[0] != name or not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsafe result archive member {member.name}")
        tf.extractall(C.CFD / "results", filter="data")
    outputs = json.loads((destination / "output_hashes.json").read_text())
    for name_in_case, expected in outputs.items():
        path = destination.joinpath(*PurePosixPath(name_in_case).parts)
        if digest(path) != expected:
            raise ValueError(f"Downloaded output hash mismatch: {path}")
    print(f"Verified {len(outputs)} downloaded output files for {name}", flush=True)
    remote(host, REMOTE_CLEAN, name, digest(destination / "run_identity.json"))
    incoming.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("--host", required=True)
    parser.add_argument("--collect", action="store_true",
                        help="download, verify and clean a case already solved and hashed by an interrupted run")
    args = parser.parse_args()
    run(args.case, args.host, args.collect)
