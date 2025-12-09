param(
  [string]$EnvFilePath = ".env",
  [string]$DevUrl = "http://localhost:5175",
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

function Invoke-Json($url, $headers) {
  try {
    $resp = Invoke-WebRequest -Uri $url -Headers $headers -UseBasicParsing -TimeoutSec 10
    $status = $resp.StatusCode
    $json = $null
    try { $json = $resp.Content | ConvertFrom-Json } catch {}
    return @{ ok = ($status -eq 200); status = $status; json = $json; raw = $resp.Content }
  } catch {
    return @{ ok = $false; status = -1; error = $_.Exception.Message }
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
    return @{ ok = $false; status = -1; error = $_.Exception.Message }
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
    return @{ ok = $false; status = -1; error = $_.Exception.Message }
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
if (-not $apiUrl) { $apiUrl = $DefaultApiUrl }
$apiBase = $apiUrl.TrimEnd('/')
$hostBase = ($apiBase -replace '/api$', '')
$headers = @{ 'X-Tenant' = 'captar' }

$results = @()
$results += Test-Endpoint 'health' ("$hostBase/health") $headers @('status','version')
$results += Test-Endpoint 'tenants' ("$apiBase/tenants") $headers @('rows','columns')
$results += Test-Endpoint 'dashboard' ("$apiBase/dashboard/stats") $headers @('total_eleitores','total_usuarios')
$results += Test-Endpoint 'usuarios' ("$apiBase/usuarios") $headers @('rows','columns')

if ($IncludeDev) {
  $devApiBase = ("$DevUrl/api").TrimEnd('/')
  $results += Test-Endpoint 'dev.tenants' ("$devApiBase/tenants") $headers @('rows','columns')
  $results += Test-Endpoint 'dev.dashboard' ("$devApiBase/dashboard/stats") $headers @('total_eleitores','total_usuarios')
  $results += Test-Endpoint 'dev.usuarios' ("$devApiBase/usuarios") $headers @('rows','columns')
}

Write-Host "=== Smoke Test (API) ==="
foreach ($r in $results) {
  $mark = if ($r.pass) { '[OK] ' } else { '[FAIL] ' }
  Write-Host ($mark + $r.name + " -> " + $r.url + " (status=" + $r.status + ")")
}

$failCount = ($results | Where-Object { -not $_.pass }).Count
if ($failCount -gt 0) {
  Write-Host "Failures: $failCount" -ForegroundColor Red
  if (-not $TenantChecks) { exit 1 }
} else {
  Write-Host "All endpoints healthy" -ForegroundColor Green
}

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
    # Login test
    $loginBody = @{ usuario = "ADMIN.$slugUpper"; senha = 'admin123' }
    $login = Invoke-JsonPost ("$apiBase/auth/login") $h $loginBody
    $okLogin = ($login.ok -and $login.json -and $login.json.token)
    $markLogin = if ($okLogin) { '[OK] ' } else { '[FAIL] ' }
    Write-Host ($markLogin + "login($slug) -> status=" + $login.status)
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
      $del = Invoke-JsonDelete ("$apiBase/usuarios/$id") $h
      $okDel = ($del.ok -and $del.json -and $del.json.deleted)
      $markDel = if ($okDel) { '[OK] ' } else { '[FAIL] ' }
      Write-Host ($markDel + "delete($slug) -> status=" + $del.status)
    }
  }
}

