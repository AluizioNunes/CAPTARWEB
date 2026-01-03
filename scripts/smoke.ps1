param(
  [string]$EnvFilePath = ".env",
  [string]$DevUrl = "http://localhost:5173",
  [string]$DefaultApiUrl = "http://localhost:8000/api",
  [switch]$IncludeDev = $false,
  [switch]$TenantChecks = $false
)

function Get-ApiUrlFromEnv($path) {
  try {
    if (Test-Path $path) {
      $line = Get-Content -Path $path | Where-Object { $_ -match '^VITE_API_URL=' } | Select-Object -First 1
      if ($line) {
        $val = $line -replace '^VITE_API_URL=', ''
        if ($val) { return $val.Trim() }
      }
    }
  } catch {}
  return $null
}

function Get-FastApiPortFromEnv($path) {
  try {
    if (Test-Path $path) {
      $line = Get-Content -Path $path | Where-Object { $_ -match '^FASTAPI_HOST_PORT=' } | Select-Object -First 1
      if ($line) {
        $val = $line -replace '^FASTAPI_HOST_PORT=', ''
        $port = 0
        if ([int]::TryParse($val.Trim(), [ref]$port) -and $port -gt 0) {
          return $port
        }
      }
    }
  } catch {}
  return $null
}

function Get-DevPortFromEnv($path) {
  try {
    if (Test-Path $path) {
      $line = Get-Content -Path $path | Where-Object { $_ -match '^VITE_DEV_PORT=' } | Select-Object -First 1
      if (-not $line) { $line = Get-Content -Path $path | Where-Object { $_ -match '^FRONTEND_HOST_PORT=' } | Select-Object -First 1 }
      if ($line) {
        $val = $line -replace '^(VITE_DEV_PORT|FRONTEND_HOST_PORT)=', ''
        $port = 0
        if ([int]::TryParse($val.Trim(), [ref]$port) -and $port -gt 0) {
          return $port
        }
      }
    }
  } catch {}
  return 5173
}

function Get-PortFromUrl($url) {
  try {
    if (-not $url) { return $null }
    $u = [System.Uri]::new($url)
    if ($u.Port -gt 0) { return [int]$u.Port }
  } catch {}
  return $null
}

function Invoke-Json($url, $headers) {
  try {
    $resp = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing -TimeoutSec 10
    $status = $resp.StatusCode
    $json = $null
    try { $json = $resp.Content | ConvertFrom-Json } catch {}
    return @{ ok = ($status -eq 200); status = $status; json = $json; raw = $resp.Content }
  } catch {
    $status = -1
    $raw = $null
    try {
      $resp = $_.Exception.Response
      if ($resp -and $resp.StatusCode) { $status = [int]$resp.StatusCode }
      try {
        $stream = $resp.GetResponseStream()
        if ($stream) {
          $reader = New-Object System.IO.StreamReader($stream)
          $raw = $reader.ReadToEnd()
          $reader.Close()
        }
      } catch {}
    } catch {}
    return @{ ok = $false; status = $status; error = $_.Exception.Message; raw = $raw }
  }
}

function Invoke-JsonPost($url, $headers, $bodyObj) {
  try {
    $jsonBody = $bodyObj | ConvertTo-Json -Depth 6
    if (-not $headers.ContainsKey('Content-Type')) { $headers['Content-Type'] = 'application/json' }
    $resp = Invoke-WebRequest -Method Post -Uri $url -Headers $headers -UseBasicParsing -TimeoutSec 10 -Body $jsonBody
    $status = $resp.StatusCode
    $json = $null
    try { $json = $resp.Content | ConvertFrom-Json } catch {}
    return @{ ok = ($status -eq 200); status = $status; json = $json; raw = $resp.Content }
  } catch {
    $status = -1
    $raw = $null
    try {
      $resp = $_.Exception.Response
      if ($resp -and $resp.StatusCode) { $status = [int]$resp.StatusCode }
      try {
        $stream = $resp.GetResponseStream()
        if ($stream) {
          $reader = New-Object System.IO.StreamReader($stream)
          $raw = $reader.ReadToEnd()
          $reader.Close()
        }
      } catch {}
    } catch {}
    $json = $null
    try { if ($raw) { $json = $raw | ConvertFrom-Json } } catch {}
    return @{ ok = $false; status = $status; error = $_.Exception.Message; raw = $raw; json = $json }
  }
}

function Invoke-JsonDelete($url, $headers) {
  try {
    $resp = Invoke-WebRequest -Method Delete -Uri $url -Headers $headers -UseBasicParsing -TimeoutSec 10
    $status = $resp.StatusCode
    $json = $null
    try { $json = $resp.Content | ConvertFrom-Json } catch {}
    return @{ ok = ($status -eq 200); status = $status; json = $json; raw = $resp.Content }
  } catch {
    $status = -1
    $raw = $null
    try {
      $resp = $_.Exception.Response
      if ($resp -and $resp.StatusCode) { $status = [int]$resp.StatusCode }
      try {
        $stream = $resp.GetResponseStream()
        if ($stream) {
          $reader = New-Object System.IO.StreamReader($stream)
          $raw = $reader.ReadToEnd()
          $reader.Close()
        }
      } catch {}
    } catch {}
    $json = $null
    try { if ($raw) { $json = $raw | ConvertFrom-Json } } catch {}
    return @{ ok = $false; status = $status; error = $_.Exception.Message; raw = $raw; json = $json }
  }
}

function Test-Endpoint($name, $url, $headers, [string[]]$expectedKeys) {
  $r = Invoke-Json $url $headers
  $hasKeys = $false
  if ($r.ok -and $r.json) {
    $keys = @()
    try { $keys = $r.json | Get-Member -MemberType NoteProperty | ForEach-Object { $_.Name } } catch {}
    if ($expectedKeys -and $expectedKeys.Count -gt 0) {
      $hasKeys = ($expectedKeys | ForEach-Object { $keys -contains $_ }) -notcontains $false
    } else { $hasKeys = $true }
  }
  return @{ name = $name; url = $url; pass = ($r.ok -and $hasKeys); status = $r.status; keysOk = $hasKeys; json = $r.json; error = $r.error }
}

$apiUrl = Get-ApiUrlFromEnv $EnvFilePath
if (-not $apiUrl -or -not ($apiUrl -match '^https?://')) {
  $port = Get-FastApiPortFromEnv $EnvFilePath
  if (-not $port) { $port = 8000 }
  $apiUrl = "http://localhost:$port/api"
}
$apiBase = $apiUrl.TrimEnd('/')
$hostBase = ($apiBase -replace '/api$', '')
$headers = @{ 'X-Tenant' = 'captar' }

$results = @()
$results += Test-Endpoint 'health' ("$hostBase/health") $headers @('status','version')
$results += Test-Endpoint 'tenants' ("$apiBase/tenants") $headers @('rows','columns')
$results += Test-Endpoint 'dashboard' ("$apiBase/dashboard/stats") $headers @('total_eleitores','total_usuarios')
$results += Test-Endpoint 'usuarios' ("$apiBase/usuarios") $headers @('rows','columns')

if ($IncludeDev) {
  $devProc = $null
  $devStarted = $false
  $devPortFromEnv = Get-DevPortFromEnv $EnvFilePath
  $devPortFromDevUrl = Get-PortFromUrl $DevUrl
  $devPortsToTry = @()
  if ($devPortFromDevUrl) { $devPortsToTry += $devPortFromDevUrl }
  if ($devPortFromEnv) { $devPortsToTry += $devPortFromEnv }
  $devPortsToTry += @(5173, 5174, 5175)
  $devPortsToTry = $devPortsToTry | Select-Object -Unique

  $devUrlsToTry = @()
  if ($DevUrl) { $devUrlsToTry += $DevUrl }
  $devUrlsToTry += ($devPortsToTry | ForEach-Object { "http://localhost:$_" }) | Where-Object { $_ -ne $DevUrl } | Select-Object -Unique

  $pickedDevUrl = $null
  foreach ($cand in $devUrlsToTry) {
    $devApiBaseTry = ("$cand/api").TrimEnd('/')
    $probe = Invoke-Json ("$devApiBaseTry/tenants") $headers
    if ($probe.status -ne -1) { $pickedDevUrl = $cand; break }
  }

  if (-not $pickedDevUrl) {
    foreach ($p in $devPortsToTry) {
      try {
        $devProc = Start-Process -FilePath "npm" -ArgumentList @("run","dev","--","--port",$p,"--host","0.0.0.0","--strictPort") -WorkingDirectory (Get-Location) -NoNewWindow -PassThru
        $devStarted = $true
      } catch {
        $devProc = $null
        $devStarted = $false
      }

      if (-not $devProc) { continue }

      $timeoutAt = (Get-Date).AddSeconds(60)
      while ((Get-Date) -lt $timeoutAt) {
        if ($devProc.HasExited) { break }
        $devApiBaseTry = ("http://localhost:$p/api").TrimEnd('/')
        $probe = Invoke-Json ("$devApiBaseTry/tenants") $headers
        if ($probe.status -ne -1) { $pickedDevUrl = "http://localhost:$p"; break }
        Start-Sleep -Milliseconds 700
      }

      if ($pickedDevUrl) { break }
      try { if (-not $devProc.HasExited) { Stop-Process -Id $devProc.Id -Force } } catch {}
      $devProc = $null
      $devStarted = $false
    }
  }

  if ($pickedDevUrl) {
    $devApiBase = ("$pickedDevUrl/api").TrimEnd('/')
    $results += Test-Endpoint 'dev.tenants' ("$devApiBase/tenants") $headers @('rows','columns')
    $results += Test-Endpoint 'dev.dashboard' ("$devApiBase/dashboard/stats") $headers @('total_eleitores','total_usuarios')
    $results += Test-Endpoint 'dev.usuarios' ("$devApiBase/usuarios") $headers @('rows','columns')
  } else {
    $results += @{ name = 'dev.tenants'; url = "$DevUrl/api/tenants"; pass = $false; status = -1; keysOk = $false; json = $null; error = 'Dev server indisponível' }
    $results += @{ name = 'dev.dashboard'; url = "$DevUrl/api/dashboard/stats"; pass = $false; status = -1; keysOk = $false; json = $null; error = 'Dev server indisponível' }
    $results += @{ name = 'dev.usuarios'; url = "$DevUrl/api/usuarios"; pass = $false; status = -1; keysOk = $false; json = $null; error = 'Dev server indisponível' }
  }
}

Write-Host "=== Smoke Test (API) ==="
foreach ($r in $results) {
  $mark = if ($r.pass) { '[OK] ' } else { '[FAIL] ' }
  Write-Host ($mark + $r.name + " -> " + $r.url + " (status=" + $r.status + ")")
}

$failCount = ($results | Where-Object { -not $_.pass }).Count
if ($failCount -gt 0) {
  Write-Host "Failures: $failCount" -ForegroundColor Red
} else {
  Write-Host "All endpoints healthy" -ForegroundColor Green
}

$tenantFailCount = 0
if ($TenantChecks) {
  Write-Host "`n=== Tenant Checks (Login + Create/Delete Usuario) ==="
  $ten = Invoke-Json ("$apiBase/tenants") $headers
  $rows = @()
  if ($ten.ok -and $ten.json) { $rows = $ten.json.rows } else { $rows = @() }
  foreach ($t in $rows) {
    $slug = ($t.Slug, $t.slug | Where-Object { $_ })[0]
    if (-not $slug) { continue }
    $slugUpper = $slug.ToUpper()
    $h = @{ 'X-Tenant' = $slug }
    # Create user test
    $tmpUser = @{ Nome = "SMOKE USER $slugUpper"; Email = "smoke.$slug@local"; Senha = '123456'; Usuario = "SMOKE.$slugUpper"; Perfil = 'COORDENADOR'; Funcao = 'COORDENADOR'; Ativo = $true }
    $cre = Invoke-JsonPost ("$apiBase/usuarios") $h $tmpUser
    $id = $null
    if ($cre.ok -and $cre.json -and $cre.json.id) { $id = [int]$cre.json.id }
    $okCreate = ($cre.ok -and $id -gt 0)
    $markCreate = if ($okCreate) { '[OK] ' } else { '[FAIL] ' }
    $idText = if ($null -ne $id) { $id } else { 0 }
    Write-Host ($markCreate + "create($slug) -> status=" + $cre.status + " id=" + $idText)
    if ($okCreate) {
      $loginBody = @{ usuario = "SMOKE.$slugUpper"; senha = '123456' }
      $login = Invoke-JsonPost ("$apiBase/auth/login") $h $loginBody
      $okLogin = ($login.ok -and $login.json -and $login.json.token)
      $markLogin = if ($okLogin) { '[OK] ' } else { '[FAIL] ' }
      Write-Host ($markLogin + "login($slug) -> status=" + $login.status)
      if (-not $okLogin) { $tenantFailCount += 1 }
      $del = Invoke-JsonDelete ("$apiBase/usuarios/$id") $h
      $okDel = ($del.ok -and $del.json -and $del.json.deleted)
      $markDel = if ($okDel) { '[OK] ' } else { '[FAIL] ' }
      Write-Host ($markDel + "delete($slug) -> status=" + $del.status)
      if (-not $okDel) { $tenantFailCount += 1 }
    } else {
      $tenantFailCount += 1
    }
  }
}

if ($IncludeDev -and $devProc -and $devStarted) {
  try {
    if (-not $devProc.HasExited) { Stop-Process -Id $devProc.Id -Force }
  } catch {}
}

if (($failCount + $tenantFailCount) -gt 0) { exit 1 }

