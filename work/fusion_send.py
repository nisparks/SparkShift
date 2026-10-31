import json, sys, urllib.error, urllib.request
path = sys.argv[1]
timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 600
code = open(path, encoding="utf-8").read() if path != "-" else sys.stdin.read()
req = urllib.request.Request("http://127.0.0.1:8765/execute", data=json.dumps({"operation": "execute", "payload": {"code": code}}).encode(),
                             headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=timeout) as r:
        print(r.read().decode()[:20000])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode(errors="replace")[:20000])
    sys.exit(1)
