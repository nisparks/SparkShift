param([Parameter(Mandatory = $true)][string[]]$Names)
# Fetch finished CFD cases from the remote host and analyse them (session helper).
$S = "C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\cfd"
$repo = "C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
$py = "C:\Users\nspar\AppData\Local\Programs\Python\Python311\python.exe"
foreach ($n in $Names) {
    $dst = "$S\results\$n"
    if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
    New-Item -ItemType Directory -Force $dst | Out-Null
    ssh -o BatchMode=yes nisparks@192.168.0.21 "cd ~/sparkshift_cfd/$n && tail -1 log.run && tar cf /tmp/$n.tar VTK postProcessing log.run log.checkMesh log.snappyHexMesh"
    scp -q -o BatchMode=yes "nisparks@192.168.0.21:/tmp/$n.tar" "$env:TEMP\$n.tar"
    tar -xf "$env:TEMP\$n.tar" -C $dst
    Remove-Item "$env:TEMP\$n.tar"
    ssh -o BatchMode=yes nisparks@192.168.0.21 "rm /tmp/$n.tar"
    Copy-Item "$S\cases\$n\domain.json", "$S\cases\$n\stages.json" $dst
    Push-Location $repo
    & $py cfd_cpap_r41.py analyse $n 2>&1 | Where-Object { $_ -notmatch "WARN\|" }
    Pop-Location
}
