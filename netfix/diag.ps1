<#
  diag.ps1 - READ-ONLY network diagnostics for Windows 10/11 (netfix kit).
  It does NOT change any system setting. It only writes text reports into
  the "out" folder next to this script.

  Run in an Administrator PowerShell:
    powershell -NoProfile -ExecutionPolicy Bypass -File C:\netfix\diag.ps1 -Since 2026-11-21
    powershell -NoProfile -ExecutionPolicy Bypass -File C:\netfix\diag.ps1 -Quick

    -Since yyyy-MM-dd  the day BEFORE the AI-agent session (default: 5 days ago)
    -Quick             fast re-check (ladder + key settings); run it after every fix

  Output (folder .\out):
    report.txt            RED FLAGS, LADDER (where it breaks), current settings
    changes.txt           what changed since -Since (services, drivers, programs, events)
    opencode_history.txt  system-changing commands found in opencode session files
    wfp_filters.xml       raw WFP filter dump (admin only)
    quick.txt             result of -Quick
#>
param(
    [string]$Since = '',
    [switch]$Quick
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
$ErrorView = 'CategoryView'
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }

# ===================== setup =====================
$Root = $PSScriptRoot
if (-not $Root) { $Root = 'C:\netfix' }
$OutDir = Join-Path $Root 'out'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$SinceDate = (Get-Date).Date.AddDays(-5)
if ($Since) {
    try { $SinceDate = [datetime]::ParseExact($Since, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture) }
    catch { Write-Host ('WARNING: bad -Since value "' + $Since + '" (expected yyyy-MM-dd). Using ' + $SinceDate.ToString('yyyy-MM-dd')) }
}
$SinceStr = $SinceDate.ToString('yyyy-MM-dd')
$SinceYmd = $SinceDate.ToString('yyyyMMdd')
$Mode = 'FULL'
if ($Quick) { $Mode = 'QUICK' }

$IsAdmin = $false
try { $IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) } catch { }

Write-Host ('netfix diag.ps1   mode=' + $Mode + '   since=' + $SinceStr + '   admin=' + $IsAdmin)
if (-not $IsAdmin) { Write-Host 'NOTE: not running as Administrator - some checks will be skipped.' }

# ===================== helpers =====================
$Flags   = New-Object System.Collections.Generic.List[string]
$Report  = New-Object System.Collections.Generic.List[string]
$Changes = New-Object System.Collections.Generic.List[string]

function Flag([string]$Text) { $script:Flags.Add($Text) }

function Cut($Value, [int]$Max = 160) {
    if ($null -eq $Value) { return '' }
    $t = (([string]$Value) -replace '\s+', ' ').Trim()
    if ($t.Length -gt $Max) { return ($t.Substring(0, $Max) + '...') }
    return $t
}

function ErrMsg($Err) {
    $x = $Err.Exception
    while ($null -ne $x.InnerException) { $x = $x.InnerException }
    return (Cut $x.Message 110)
}

function Tbl($Data) {
    $rows = @($Data | Where-Object { $null -ne $_ })
    if ($rows.Count -eq 0) { return '(none)' }
    return (($rows | Format-Table -AutoSize -Wrap | Out-String -Width 220).Trim())
}

function Try-Get([scriptblock]$Block) {
    try { & $Block } catch { }
}

function Add-Section($List, [string]$Title, [scriptblock]$Body) {
    Write-Host ('  ... ' + $Title)
    $txt = ''
    try { $txt = ((& $Body 2>&1) | Out-String -Width 220).Trim() }
    catch { $txt = 'SECTION ERROR: ' + (ErrMsg $_) }
    if (-not $txt) { $txt = '(nothing found)' }
    $List.Add('')
    $List.Add('===== ' + $Title + ' =====')
    $List.Add($txt)
}

function Get-ProcName($ProcId) {
    try { return (Get-Process -Id ([int]$ProcId) -ErrorAction Stop).ProcessName } catch { return '?' }
}

function Get-Ports([string]$Text) {
    $found = @()
    if ($Text) { foreach ($m in [regex]::Matches($Text, ':(\d{2,5})')) { $found += [int]$m.Groups[1].Value } }
    return @($found | Select-Object -Unique)
}

function Test-LocalAddr([string]$Text) { return ($Text -match '127\.0\.0\.1|localhost|\[::1\]') }

function Test-ListenPort([int]$Port) {
    $m = @($script:Listen | Where-Object { $_.LocalPort -eq $Port })
    if ($m.Count -gt 0) { return ('LISTENING (' + (Get-ProcName $m[0].OwningProcess) + ')') }
    return 'NOT LISTENING -> DEAD PROXY'
}

function IsOk($Value) { return ([string]$Value).StartsWith('OK') }

function Test-Ping([string]$Ip) {
    try {
        $p = New-Object System.Net.NetworkInformation.Ping
        $last = ''
        foreach ($n in 1..2) {
            $r = $p.Send($Ip, 1500)
            if ($r.Status -eq [System.Net.NetworkInformation.IPStatus]::Success) { return ('OK ' + $r.RoundtripTime + ' ms') }
            $last = [string]$r.Status
        }
        return ('FAIL ' + $last)
    } catch { return ('FAIL ' + (ErrMsg $_)) }
}

function Test-Tcp([string]$HostName, [int]$Port, [int]$TimeoutMs = 3000) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $ar = $c.BeginConnect($HostName, $Port, $null, $null)
        if (-not $ar.AsyncWaitHandle.WaitOne($TimeoutMs)) { return 'FAIL timeout' }
        $c.EndConnect($ar)
        return 'OK'
    } catch { return ('FAIL ' + (ErrMsg $_)) }
    finally { $c.Close() }
}

function Test-Dns([string]$Name, [string]$Server) {
    try {
        if ($Server) { $r = Resolve-DnsName -Name $Name -Type A -Server $Server -DnsOnly -QuickTimeout -ErrorAction Stop }
        else { $r = Resolve-DnsName -Name $Name -Type A -QuickTimeout -ErrorAction Stop }
        $ips = @($r | Where-Object { [string]$_.Type -eq 'A' } | ForEach-Object { [string]$_.IPAddress } | Select-Object -First 2)
        if ($ips.Count -gt 0) { return ('OK ' + ($ips -join ',')) }
        return 'FAIL no A record'
    } catch { return ('FAIL ' + (ErrMsg $_)) }
}

$CurlExe = Join-Path $env:SystemRoot 'System32\curl.exe'
function Test-Curl([string]$Url, [switch]$NoProxy) {
    if (-not (Test-Path -LiteralPath $script:CurlExe)) { return 'SKIP no curl.exe' }
    $cargs = @('-sS', '--stderr', '-', '--ssl-no-revoke', '-m', '10', '-o', 'NUL', '-w', '%{http_code}')
    if ($NoProxy) { $cargs += @('--noproxy', '*') }
    $cargs += $Url
    try {
        $res = Cut ((& $script:CurlExe @cargs) -join ' ') 140
        if ($res -match '^[1-5]\d\d$') { return ('OK HTTP ' + $res) }
        return ('FAIL ' + $res)
    } catch { return ('FAIL ' + (ErrMsg $_)) }
}

function Test-Iwr([string]$Url) {
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 5 -ErrorAction Stop
        return ('OK HTTP ' + [int]$r.StatusCode)
    } catch {
        $code = 0
        try { $code = [int]$_.Exception.Response.StatusCode } catch { }
        if ($code -gt 0) { return ('OK HTTP ' + $code + ' (server answered)') }
        return ('FAIL ' + (ErrMsg $_))
    }
}

# ===================== core facts =====================
Write-Host '  ... reading adapters, IP, routes, DNS, proxy, services, firewall'
$Pat = 'windivert|wintun|tap0901|tap-windows|wireguard|openvpn|zapret|winws|goodbye|byedpi|ciadpi|xray|v2ray|sing-?box|clash|mihomo|hiddify|nekobox|nekoray|throne|\bwarp\b|cloudflare|amnezia|outline|proxifier|npcap|\bnpf\b|vboxnet|vmnet|portmaster|safing|simplewall|tinywall|glasswire|adguard|psiphon|\bhapp\b|v2raytun|shadowsocks|ss-local|hysteria|tun2socks|tun2proxy|privoxy|dnscrypt|yogadns|tailscale|zerotier|hamachi|radmin|softether|protonvpn|nordvpn|windscribe|mullvad|\bvpn\b'

$Os          = Try-Get { Get-CimInstance Win32_OperatingSystem -ErrorAction Stop }
$Adapters    = @(Try-Get { Get-NetAdapter -ErrorAction Stop })
$Physical    = @(Try-Get { Get-NetAdapter -Physical -ErrorAction Stop })
$Wired       = @($Physical | Where-Object { [string]$_.PhysicalMediaType -eq '802.3' })
$PhysIdx     = @($Physical | ForEach-Object { $_.ifIndex })
$UpIdx       = @($Adapters | Where-Object { [string]$_.Status -eq 'Up' } | ForEach-Object { $_.ifIndex })
$IPv4        = @(Try-Get { Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop })
$IfV4        = @(Try-Get { Get-NetIPInterface -AddressFamily IPv4 -ErrorAction Stop })
$Routes      = @(Try-Get { Get-NetRoute -AddressFamily IPv4 -PolicyStore ActiveStore -ErrorAction Stop })
$DefRoutes   = @($Routes | Where-Object { @('0.0.0.0/0', '0.0.0.0/1', '128.0.0.0/1') -contains [string]$_.DestinationPrefix })
$PersRoutes  = @(Try-Get { Get-NetRoute -PolicyStore PersistentStore -ErrorAction Stop })
$Gateways    = @($DefRoutes | Where-Object { [string]$_.DestinationPrefix -eq '0.0.0.0/0' -and $_.NextHop -and [string]$_.NextHop -ne '0.0.0.0' } | ForEach-Object { [string]$_.NextHop } | Select-Object -Unique)
$DnsSrv      = @(Try-Get { Get-DnsClientServerAddress -ErrorAction Stop | Where-Object { $_.ServerAddresses } })
$Listen      = @(Try-Get { Get-NetTCPConnection -State Listen -ErrorAction Stop })
$Udp53       = @(Try-Get { Get-NetUDPEndpoint -LocalPort 53 -ErrorAction Stop })
$Nrpt        = @(Try-Get { Get-DnsClientNrptRule -ErrorAction Stop })
$HostsPath   = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
$HostsActive = @(Try-Get { Get-Content -LiteralPath $HostsPath -ErrorAction Stop | Where-Object { $_ -notmatch '^\s*(#|$)' } })
$Inet        = Try-Get { Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction Stop }
$ProxyEnable = 0
$ProxyServer = ''
$PacUrl = ''
if ($Inet) {
    $ProxyEnable = [int]$Inet.ProxyEnable
    $ProxyServer = [string]$Inet.ProxyServer
    $PacUrl = [string]$Inet.AutoConfigURL
}
$WinHttp = [string](Try-Get { & netsh.exe winhttp show proxy 2>&1 | Out-String })
$EnvProxies = @()
foreach ($scope in @('Process', 'User', 'Machine')) {
    foreach ($vname in @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY')) {
        $v = $null
        try { $v = [Environment]::GetEnvironmentVariable($vname, $scope) } catch { }
        if ($v) { $EnvProxies += ($scope + ' ' + $vname + '=' + $v) }
    }
}
$SvcAll     = @(Try-Get { Get-CimInstance Win32_Service -ErrorAction Stop })
$DrvAll     = @(Try-Get { Get-CimInstance Win32_SystemDriver -ErrorAction Stop })
$SvcHit     = @($SvcAll | Where-Object { ([string]$_.Name + ' ' + [string]$_.DisplayName + ' ' + [string]$_.PathName) -match $Pat })
$DrvHit     = @($DrvAll | Where-Object { ([string]$_.Name + ' ' + [string]$_.DisplayName + ' ' + [string]$_.PathName) -match $Pat })
$ProcHit    = @(Try-Get { Get-Process -ErrorAction Stop | Where-Object { $_.ProcessName -match $Pat } } | Sort-Object ProcessName -Unique)
$FwProf     = @(Try-Get { Get-NetFirewallProfile -ErrorAction Stop })
$FwOutBlock = @(Try-Get { Get-NetFirewallRule -Direction Outbound -Action Block -Enabled True -ErrorAction Stop })
$WsDlls     = @(Try-Get { & netsh.exe winsock show catalog 2>$null | Select-String -Pattern '\.dll' | ForEach-Object { ($_.Line -replace '^.*?(%|[A-Za-z]:\\)', '$1').Trim() } | Sort-Object -Unique })
$Ncsi       = Try-Get { Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\NlaSvc\Parameters\Internet' -ErrorAction Stop }
$VmSw       = @()
if (Get-Command Get-VMSwitch -ErrorAction SilentlyContinue) { $VmSw = @(Try-Get { Get-VMSwitch -ErrorAction Stop }) }
$WiredBind  = @(foreach ($a in $Wired) { Try-Get { Get-NetAdapterBinding -Name $a.Name -AllBindings -ErrorAction Stop } })
$PnpNet     = @(Try-Get { Get-PnpDevice -Class Net -ErrorAction Stop | Where-Object { [string]$_.InstanceId -match '^(PCI|USB)\\' } })
$PnpBad     = @(Try-Get { Get-PnpDevice -PresentOnly -Status ERROR, DEGRADED, UNKNOWN -ErrorAction Stop | Where-Object { [string]$_.InstanceId -match '^(PCI|USB)\\' } })
$PnpBadInfo = @(foreach ($d in $PnpBad) {
    $pc = $null
    $cids = ''
    try { $pc = (Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName 'DEVPKEY_Device_ProblemCode' -ErrorAction Stop).Data } catch { }
    try { $cids = [string]((Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName 'DEVPKEY_Device_CompatibleIds' -ErrorAction Stop).Data -join ' ') } catch { }
    $isNet = ($cids -match 'CC_02|Class_02') -or ([string]$d.FriendlyName -match 'Ethernet|Network|LAN|GbE|Realtek|Killer|Intel.*Connection') -or ([string]$d.Class -eq 'Net')
    [pscustomobject]@{ Name = (Cut $d.FriendlyName 55); Class = [string]$d.Class; Status = [string]$d.Status; Problem = $pc; NetDevice = $isNet }
})

# ===================== red flags: device / link / IP =====================
if ($Wired.Count -eq 0) { Flag 'NO wired Ethernet (802.3) adapter is visible to Windows -> driver missing/broken, or the device is disabled in Device Manager.' }
foreach ($d in $PnpBadInfo) {
    if ($d.NetDevice) { Flag ("Network device with a Device Manager problem: '" + $d.Name + "' status=" + $d.Status + ' code=' + $d.Problem + ' (28 = no driver, 22 = disabled, 10/43 = driver or device error).') }
}
foreach ($a in $Wired) {
    $aName = [string]$a.Name
    if ([string]$a.Status -ne 'Up') { Flag ("Wired adapter '" + $aName + "' status=" + $a.Status + ', media=' + $a.MediaConnectionState + ' (Disconnected = no link, Disabled = switched off).') }
    $ips = @($IPv4 | Where-Object { $_.InterfaceIndex -eq $a.ifIndex })
    if ([string]$a.Status -eq 'Up' -and $ips.Count -eq 0) { Flag ("Wired adapter '" + $aName + "' is Up but has NO IPv4 address.") }
    foreach ($ip in $ips) {
        if ([string]$ip.IPAddress -like '169.254.*') { Flag ("Wired adapter '" + $aName + "' has APIPA address " + $ip.IPAddress + ' -> DHCP from the router FAILED.') }
        if ([string]$ip.PrefixOrigin -eq 'Manual') { Flag ("Wired adapter '" + $aName + "' has a STATIC IPv4 " + $ip.IPAddress + '/' + $ip.PrefixLength + ' (set by hand or by the agent?).') }
    }
    $if4 = @($IfV4 | Where-Object { $_.InterfaceIndex -eq $a.ifIndex }) | Select-Object -First 1
    if ($if4) {
        if ([string]$if4.Dhcp -eq 'Disabled') { Flag ("DHCP is DISABLED on wired adapter '" + $aName + "'.") }
        if ($if4.NlMtu -and (([int]$if4.NlMtu -lt 1400) -or ([int]$if4.NlMtu -gt 1500))) { Flag ('Unusual IPv4 MTU ' + $if4.NlMtu + " on '" + $aName + "'.") }
    }
    $tp = Try-Get { Get-ItemProperty -Path ('HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\' + $a.InterfaceGuid) -ErrorAction Stop }
    if ($tp -and $tp.NameServer) { Flag ("STATIC DNS servers on wired adapter '" + $aName + "': " + $tp.NameServer) }
    $sd = Try-Get { Get-NetAdapterAdvancedProperty -Name $aName -RegistryKeyword '*SpeedDuplex' -ErrorAction Stop }
    $sdv = [string](@($sd | ForEach-Object { $_.RegistryValue }) | Select-Object -First 1)
    if ($sdv -and $sdv -ne '0') { Flag ("Speed/Duplex on '" + $aName + "' is FORCED to '" + (@($sd)[0].DisplayValue) + "' (normally Auto Negotiation).") }
    $b = @($WiredBind | Where-Object { [string]$_.Name -eq $aName })
    if ($b.Count -gt 0) {
        $tcp = @($b | Where-Object { [string]$_.ComponentID -eq 'ms_tcpip' })
        if ($tcp.Count -eq 0 -or -not $tcp[0].Enabled) { Flag ("IPv4 (ms_tcpip) is NOT enabled on wired adapter '" + $aName + "'.") }
        foreach ($x in $b) {
            if ($x.Enabled -and ([string]$x.ComponentID -notmatch '^ms_')) { Flag ("Non-Microsoft component bound to '" + $aName + "': " + $x.DisplayName + ' [' + $x.ComponentID + ']') }
        }
    }
}

# ===================== red flags: routing / DNS / proxy =====================
foreach ($r in $DefRoutes) {
    if ($PhysIdx -notcontains $r.InterfaceIndex) { Flag ('Route ' + $r.DestinationPrefix + " goes via NON-physical interface '" + $r.InterfaceAlias + "' (VPN/TUN/virtual), next hop " + $r.NextHop + ', metric ' + $r.RouteMetric + '.') }
}
if (@($DefRoutes | Where-Object { [string]$_.DestinationPrefix -ne '0.0.0.0/0' }).Count -gt 0) { Flag 'Split routes 0.0.0.0/1 + 128.0.0.0/1 exist -> a VPN/TUN captures all traffic.' }
if ($PersRoutes.Count -gt 0) { Flag ([string]$PersRoutes.Count + ' persistent (route -p) route(s) exist -> check they are correct.') }
foreach ($dn in $DnsSrv) {
    if ($UpIdx -notcontains $dn.InterfaceIndex) { continue }
    foreach ($s in @($dn.ServerAddresses)) {
        if ([string]$s -like '127.*' -or [string]$s -eq '::1') {
            $state = 'NOTHING listens on UDP 53 -> DEAD local DNS'
            if ($Udp53.Count -gt 0) { $state = 'UDP 53 listener: ' + (Get-ProcName $Udp53[0].OwningProcess) }
            Flag ("DNS server on '" + $dn.InterfaceAlias + "' is LOCAL " + $s + ' (' + $state + ').')
        }
    }
}
if ($Nrpt.Count -gt 0) { Flag ([string]$Nrpt.Count + ' NRPT DNS policy rule(s) exist (VPN leftovers can break DNS).') }
if ($HostsActive.Count -gt 0) { Flag ('hosts file has ' + $HostsActive.Count + ' active line(s) -> see DNS section.') }
if (@($HostsActive | Where-Object { $_ -match 'msftconnecttest|msftncsi' }).Count -gt 0) { Flag 'hosts overrides msftconnecttest/msftncsi -> tray icon may say "No Internet".' }
if ($ProxyEnable -eq 1) {
    $msg = "SYSTEM PROXY (WinINET) is ON: '" + $ProxyServer + "'"
    if (Test-LocalAddr $ProxyServer) { foreach ($port in (Get-Ports $ProxyServer)) { $msg += '; port ' + $port + ' ' + (Test-ListenPort $port) } }
    Flag $msg
}
if ($PacUrl) {
    $msg = "PAC script (AutoConfigURL) is set: '" + $PacUrl + "'"
    if (Test-LocalAddr $PacUrl) { foreach ($port in (Get-Ports $PacUrl)) { $msg += '; port ' + $port + ' ' + (Test-ListenPort $port) } }
    Flag $msg
}
if ($WinHttp -match '\S+:\d{2,5}') { Flag 'WinHTTP proxy is SET (netsh winhttp show proxy) -> affects Windows services and updates.' }
foreach ($ev in $EnvProxies) { if ($ev -notmatch 'NO_PROXY') { Flag ('Proxy environment variable: ' + $ev) } }

# ===================== red flags: software / firewall / stack =====================
foreach ($s in $SvcHit) { Flag ('VPN/proxy/DPI-type SERVICE: ' + $s.Name + ' [' + $s.State + ', ' + $s.StartMode + '] ' + (Cut $s.PathName 100)) }
foreach ($s in $DrvHit) { Flag ('VPN/proxy/DPI-type DRIVER: ' + $s.Name + ' [' + $s.State + ', ' + $s.StartMode + '] ' + (Cut $s.PathName 100)) }
foreach ($p in $ProcHit) { Flag ('VPN/proxy/DPI-type PROCESS running: ' + $p.ProcessName + ' (pid ' + $p.Id + ')') }
foreach ($fp in $FwProf) {
    if ([string]$fp.Enabled -eq 'True' -and [string]$fp.DefaultOutboundAction -eq 'Block') { Flag ('Firewall profile ' + $fp.Name + ': DefaultOutboundAction=BLOCK (all outbound traffic blocked unless allowed).') }
}
if ($FwOutBlock.Count -gt 0) { Flag ([string]$FwOutBlock.Count + ' enabled OUTBOUND BLOCK firewall rule(s), e.g.: ' + (Cut ((@($FwOutBlock | Select-Object -First 5 | ForEach-Object { [string]$_.DisplayName })) -join '; ') 200)) }
$WsKnown = @('mswsock.dll', 'napinsp.dll', 'pnrpnsp.dll', 'wshbth.dll', 'nlaapi.dll', 'winrnr.dll', 'wshqos.dll', 'wshhyperv.dll', 'hvsocket.dll', 'wshtcpip.dll', 'rsvpsp.dll', 'mdnsnsp.dll', 'vsocklib.dll')
foreach ($w in $WsDlls) {
    $fn = ''
    try { $fn = [IO.Path]::GetFileName(([string]$w).Trim([char[]]@('"', ' '))).ToLower() } catch { }
    if ($fn -and ($WsKnown -notcontains $fn)) { Flag ('Non-standard Winsock provider DLL (possible LSP hijack): ' + $w) }
}
if ($SvcAll.Count -gt 0) {
    foreach ($n in @('Dhcp', 'Dnscache', 'nsi', 'BFE', 'MpsSvc', 'NlaSvc', 'Wcmsvc')) {
        $s = @($SvcAll | Where-Object { [string]$_.Name -eq $n }) | Select-Object -First 1
        if (-not $s) { Flag ("Core network service '" + $n + "' NOT FOUND.") }
        elseif ([string]$s.State -ne 'Running' -or [string]$s.StartMode -eq 'Disabled') { Flag ('Core network service ' + $n + ': State=' + $s.State + ', StartMode=' + $s.StartMode) }
    }
}
if ($DrvAll.Count -gt 0) {
    foreach ($n in @('AFD', 'Tcpip', 'NDIS')) {
        $s = @($DrvAll | Where-Object { [string]$_.Name -eq $n }) | Select-Object -First 1
        if ($s -and ([string]$s.State -ne 'Running' -or [string]$s.StartMode -eq 'Disabled')) { Flag ('Core network driver ' + $n + ': State=' + $s.State + ', StartMode=' + $s.StartMode) }
    }
}
if ($Ncsi -and ($null -ne $Ncsi.EnableActiveProbing) -and ([int]$Ncsi.EnableActiveProbing -eq 0)) { Flag 'NCSI active probing is DISABLED -> tray may say "No Internet" although internet works.' }
foreach ($s in $VmSw) { if ([string]$s.SwitchType -eq 'External') { Flag ("Hyper-V EXTERNAL switch '" + $s.Name + "' is bound to '" + $s.NetAdapterInterfaceDescription + "' -> host traffic must go through its vEthernet adapter.") } }
if ((Get-Date).Year -lt 2025) { Flag ('System clock looks WRONG: ' + (Get-Date) + ' -> HTTPS fails.') }

# ===================== connectivity ladder =====================
Write-Host '  ... connectivity ladder (up to ~1 minute)'
$L = [ordered]@{}
if ($Gateways.Count -eq 0) { $L['PING router (gateway)'] = 'FAIL no default gateway' }
foreach ($g in $Gateways) { $L['PING router ' + $g] = Test-Ping $g }
foreach ($ip in @('77.88.8.8', '8.8.8.8', '1.1.1.1')) { $L['PING ' + $ip] = Test-Ping $ip }
$L['TCP 77.88.8.8:53'] = Test-Tcp '77.88.8.8' 53
$L['TCP 8.8.8.8:443'] = Test-Tcp '8.8.8.8' 443
$L['TCP 1.1.1.1:443'] = Test-Tcp '1.1.1.1' 443
$L['DNS system: ya.ru'] = Test-Dns 'ya.ru' ''
$L['DNS @77.88.8.8: ya.ru'] = Test-Dns 'ya.ru' '77.88.8.8'
$L['DNS @8.8.8.8: ya.ru'] = Test-Dns 'ya.ru' '8.8.8.8'
$L['TCP ya.ru:443'] = Test-Tcp 'ya.ru' 443
$L['HTTPS curl (env proxy): ya.ru'] = Test-Curl 'https://ya.ru'
$L['HTTPS curl --noproxy: ya.ru'] = Test-Curl 'https://ya.ru' -NoProxy
$L['HTTPS curl --noproxy: google'] = Test-Curl 'https://www.google.com/generate_204' -NoProxy
$L['HTTPS system proxy (IWR): ya.ru'] = Test-Iwr 'https://ya.ru'

$gwOk = $false
foreach ($k in @($L.Keys)) { if (([string]$k).StartsWith('PING router') -and (IsOk $L[$k])) { $gwOk = $true } }
$ipOk = (IsOk $L['PING 77.88.8.8']) -or (IsOk $L['PING 8.8.8.8']) -or (IsOk $L['PING 1.1.1.1']) -or (IsOk $L['TCP 77.88.8.8:53']) -or (IsOk $L['TCP 8.8.8.8:443']) -or (IsOk $L['TCP 1.1.1.1:443'])
$dnsSys = IsOk $L['DNS system: ya.ru']
$dnsDir = (IsOk $L['DNS @77.88.8.8: ya.ru']) -or (IsOk $L['DNS @8.8.8.8: ya.ru'])
$tcpSite = IsOk $L['TCP ya.ru:443']
$curlEnv = IsOk $L['HTTPS curl (env proxy): ya.ru']
$curlNo = (IsOk $L['HTTPS curl --noproxy: ya.ru']) -or (IsOk $L['HTTPS curl --noproxy: google'])
$iwrOk = IsOk $L['HTTPS system proxy (IWR): ya.ru']
$wiredUp = (@($Wired | Where-Object { [string]$_.Status -eq 'Up' }).Count -gt 0)

if ($Wired.Count -eq 0) { $Breaks = 'L1/L2 DEVICE: no wired Ethernet adapter is visible -> driver/device problem (RED FLAGS, WIRED ADAPTER, driver installs in changes.txt).' }
elseif (-not $wiredUp) { $Breaks = 'L1/L2 LINK: the wired adapter is not Up (no link / disabled / driver) -> WIRED ADAPTER section.' }
elseif ($Gateways.Count -eq 0) { $Breaks = 'L3 IP: no default gateway -> DHCP failed or broken static IP config (IPV4 CONFIG).' }
elseif ((-not $gwOk) -and (-not $ipOk)) { $Breaks = 'LAN: the router does not answer and internet IPs fail -> IP config, firewall/WFP block, filter driver, VPN kill switch.' }
elseif (-not $ipOk) { $Breaks = 'ROUTING: router OK but internet IPs fail -> default route hijack (VPN/TUN), kill switch, outbound firewall block, DPI tool.' }
elseif ((-not $dnsSys) -and $dnsDir) { $Breaks = 'DNS CONFIG: direct DNS works, system DNS fails -> adapter DNS servers, NRPT, dead local DNS proxy, Dnscache service.' }
elseif (-not $dnsSys) { $Breaks = 'DNS BLOCKED: IPs work but no DNS at all -> UDP/53 blocked (firewall/VPN/DPI) or DNS client broken.' }
elseif ($curlNo -and (-not $iwrOk)) { $Breaks = 'SYSTEM PROXY: direct HTTPS works, the system-proxy path fails -> WinINET proxy / PAC left on (browsers use it).' }
elseif ($curlNo -and (-not $curlEnv)) { $Breaks = 'ENV PROXY: HTTP(S)_PROXY variables point to a dead proxy (command-line tools fail).' }
elseif ((-not $curlNo) -and $tcpSite) { $Breaks = 'TLS/HTTPS: TCP 443 connects but HTTPS fails -> DPI tool (zapret/winws/GoodbyeDPI), HTTPS filtering, wrong clock, Winsock LSP.' }
elseif (-not $curlNo) { $Breaks = 'HTTPS: DNS works but HTTPS and TCP to the site fail -> firewall/VPN/DPI (compare the TCP lines).' }
else { $Breaks = 'NOTHING BROKEN from PowerShell -> the problem is browser-only (browser proxy/extension) or just the tray icon (NCSI).' }

$LadderLines = New-Object System.Collections.Generic.List[string]
$routeInfo = 'NONE'
if ($DefRoutes.Count -gt 0) { $routeInfo = (@($DefRoutes | ForEach-Object { [string]$_.InterfaceAlias + ' -> ' + $_.NextHop + ' (' + $_.DestinationPrefix + ', metric ' + $_.RouteMetric + ')' })) -join '; ' }
$LadderLines.Add('Default route(s) via: ' + $routeInfo)
foreach ($k in @($L.Keys)) { $LadderLines.Add(([string]$k).PadRight(36) + ' ' + $L[$k]) }
$LadderLines.Add('BREAKS AT: ' + $Breaks)

# ===================== FULL mode: what changed since -Since =====================
$TaskHit = @()
$Startup = @()
$WfpTop = $null
$WfpHit = @()
$Ev7045 = @()
$Ev7040Rel = @()
$EvMsi = @()
$NewApps = @()
$NewDirs = @()
$NewDl = @()
$Hotfix = @()
$DrvInst = @()
$SysErr = @()
$Rp = @()
$OcDirs = @()
$OcHits = New-Object System.Collections.Generic.List[string]
$OcScanned = 0

if (-not $Quick) {
    Write-Host '  ... scheduled tasks and autostart'
    $TaskHit = @(Try-Get { Get-ScheduledTask -ErrorAction Stop | Where-Object { ([string]$_.TaskName + ' ' + [string]$_.TaskPath + ' ' + ((@($_.Actions) | ForEach-Object { [string]$_.Execute + ' ' + [string]$_.Arguments }) -join ' ')) -match $Pat } })
    $Startup = @(Try-Get { Get-CimInstance Win32_StartupCommand -ErrorAction Stop })

    if ($IsAdmin) {
        Write-Host '  ... dumping WFP filters (10-60 s)'
        $wfpFile = Join-Path $OutDir 'wfp_filters.xml'
        try {
            & netsh.exe wfp show filters ('file=' + $wfpFile) 2>&1 | Out-Null
            if (Test-Path -LiteralPath $wfpFile) {
                $names = @(Select-String -LiteralPath $wfpFile -Pattern '<name>([^<]+)</name>' -AllMatches | ForEach-Object { foreach ($mm in $_.Matches) { $mm.Groups[1].Value } })
                $WfpTop = @($names | Group-Object | Sort-Object Count -Descending | Select-Object -First 25 -Property Count, Name)
                $WfpHit = @($names | Where-Object { $_ -match $Pat } | Select-Object -Unique)
            }
        } catch { }
    }

    Write-Host '  ... event logs (installed services, MSI, System errors)'
    $Ev7045 = @(Try-Get { Get-WinEvent -FilterHashtable @{ LogName = 'System'; Id = 7045; StartTime = $SinceDate } -ErrorAction Stop })
    $Noise7040 = @('BITS', 'wuauserv', 'TrustedInstaller', 'UsoSvc', 'WaaSMedicSvc', 'edgeupdate', 'edgeupdatem', 'gupdate', 'gupdatem', 'sppsvc', 'MapsBroker', 'DoSvc', 'InstallService', 'MicrosoftEdgeElevationService', 'GoogleChromeElevationService')
    $Ev7040Rel = @(Try-Get { Get-WinEvent -FilterHashtable @{ LogName = 'System'; Id = 7040; StartTime = $SinceDate } -ErrorAction Stop } | Where-Object { $Noise7040 -notcontains [string]$_.Properties[3].Value })
    $EvMsi = @(Try-Get { Get-WinEvent -FilterHashtable @{ LogName = 'Application'; ProviderName = 'MsiInstaller'; Id = 1033, 1034, 11707, 11724; StartTime = $SinceDate } -ErrorAction Stop })
    $SysErr = @(Try-Get { Get-WinEvent -FilterHashtable @{ LogName = 'System'; Level = 1, 2, 3; StartTime = $SinceDate } -MaxEvents 3000 -ErrorAction Stop })

    Write-Host '  ... installed programs, new folders, updates, driver installs'
    $NewApps = @(Get-ItemProperty -Path @('HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*') -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -and $_.InstallDate -and ([string]$_.InstallDate -ge $SinceYmd) })
    $Roots = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:ProgramData, $env:LOCALAPPDATA, (Join-Path $env:LOCALAPPDATA 'Programs'), $env:APPDATA, $env:USERPROFILE, (Join-Path $env:USERPROFILE 'Downloads'), (Join-Path $env:USERPROFILE 'Desktop'), (Join-Path $env:USERPROFILE 'scoop\apps'), (Join-Path $env:ProgramData 'chocolatey\lib'), ($env:SystemDrive + '\'))
    $NewDirs = @(foreach ($rt in $Roots) { if ($rt -and (Test-Path -LiteralPath $rt)) { Get-ChildItem -LiteralPath $rt -Directory -Force -ErrorAction SilentlyContinue | Where-Object { $_.CreationTime -ge $SinceDate } } })
    $NewDl = @(Try-Get { Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE 'Downloads') -File -Force -ErrorAction Stop | Where-Object { $_.CreationTime -ge $SinceDate } })
    $Hotfix = @(Try-Get { Get-HotFix -ErrorAction Stop | Where-Object { $_.InstalledOn -and $_.InstalledOn -ge $SinceDate } })
    $SetupApi = Join-Path $env:SystemRoot 'INF\setupapi.dev.log'
    $DrvInst = @(Try-Get {
        Select-String -LiteralPath $SetupApi -Pattern '^>>>\s+\[' -Context 0, 1 -ErrorAction Stop | ForEach-Object {
            $post = [string]($_.Context.PostContext -join ' ')
            if ($post -match '(\d{4})/(\d{2})/(\d{2}) (\d{2}:\d{2})') {
                $dt = (Get-Date -Year ([int]$matches[1]) -Month ([int]$matches[2]) -Day ([int]$matches[3])).Date
                if ($dt -ge $SinceDate) { $matches[1] + '-' + $matches[2] + '-' + $matches[3] + ' ' + $matches[4] + ' | ' + (Cut ($_.Line -replace '^>>>\s+', '') 130) }
            }
        }
    } | Select-Object -Last 25)

    Write-Host '  ... restore points'
    $Rp = @(Try-Get { Get-ComputerRestorePoint -ErrorAction Stop })

    Write-Host '  ... searching opencode session files for system-changing commands (max 90 s)'
    $OcPat = 'winget|choco(\.exe)? |scoop |pip3? (install|uninstall)|npm (i|install|uninstall|remove) |netsh|reg(\.exe)? (add|delete|import)|Set-ItemProperty|Remove-ItemProperty|NetFirewallRule|route(\.exe)? (add|delete|change|-p)|Set-DnsClient|New-NetIPAddress|Remove-NetIPAddress|Set-NetIPInterface|Set-NetAdapter|Disable-NetAdapter|Enable-NetAdapter|NetAdapterBinding|sc(\.exe)? (create|config|delete|stop)|New-Service|Set-Service|Stop-Service|pnputil|devcon|bcdedit|ipconfig /release|winsock|zapret|winws|goodbye|byedpi|v2ray|xray|sing-box|clash|mihomo|hiddify|nekobox|nekoray|warp-cli|wireguard|amnezia|ProxyEnable|ProxyServer|HTTPS?_PROXY|etc\\+hosts'
    $OcDirs = @((Join-Path $env:USERPROFILE '.local\share\opencode'), (Join-Path $env:LOCALAPPDATA 'opencode'), (Join-Path $env:APPDATA 'opencode'), (Join-Path $env:USERPROFILE '.opencode'))
    $seen = @{}
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $stop = $false
    foreach ($dir in $OcDirs) {
        if ($stop) { break }
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        $files = @(Get-ChildItem -LiteralPath $dir -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge $SinceDate -and $_.Length -lt 200MB } | Sort-Object LastWriteTime)
        foreach ($f in $files) {
            if ($sw.Elapsed.TotalSeconds -gt 90 -or $OcHits.Count -ge 400) { $OcHits.Add('(scan stopped: time or size limit)'); $stop = $true; break }
            $OcScanned++
            foreach ($m in @(Select-String -LiteralPath $f.FullName -Pattern $OcPat -ErrorAction SilentlyContinue)) {
                $line = [string]$m.Line
                $start = [Math]::Max(0, $m.Matches[0].Index - 60)
                $len = [Math]::Min(220, $line.Length - $start)
                $snip = Cut ($line.Substring($start, $len)) 220
                if (-not $seen.ContainsKey($snip)) {
                    $seen[$snip] = 1
                    $OcHits.Add($f.LastWriteTime.ToString('MM-dd HH:mm') + ' | ' + $snip)
                }
            }
        }
    }

    # ----- red flags from history -----
    if ($Ev7045.Count -gt 0) { Flag ([string]$Ev7045.Count + ' service(s)/driver(s) INSTALLED since ' + $SinceStr + ': ' + (Cut ((@($Ev7045 | ForEach-Object { [string]$_.Properties[0].Value } | Select-Object -Unique)) -join ', ') 230)) }
    if ($Ev7040Rel.Count -gt 0) { Flag ('Service start type CHANGED since ' + $SinceStr + ': ' + (Cut ((@($Ev7040Rel | ForEach-Object { [string]$_.Properties[0].Value + ' (' + [string]$_.Properties[1].Value + ' -> ' + [string]$_.Properties[2].Value + ')' } | Select-Object -Unique -First 8)) -join '; ') 260)) }
    if ($NewApps.Count -gt 0) { Flag ('Programs installed since ' + $SinceStr + ': ' + (Cut ((@($NewApps | ForEach-Object { [string]$_.DisplayName } | Select-Object -Unique)) -join ', ') 230)) }
    foreach ($nd in @($NewDirs | Where-Object { $_.Name -match $Pat } | Select-Object -First 6)) { Flag ('New folder with a VPN/DPI-type name since ' + $SinceStr + ': ' + $nd.FullName) }
    if ($DrvInst.Count -gt 0) { Flag ([string]$DrvInst.Count + ' driver install/import record(s) since ' + $SinceStr + ' (setupapi) -> see DRIVER INSTALLS in changes.txt.') }
    foreach ($w in @($WfpHit | Select-Object -First 8)) { Flag ('WFP filter from VPN/DPI software is present: ' + $w) }
    foreach ($t in $TaskHit) { Flag ('VPN/proxy/DPI-type SCHEDULED TASK: ' + $t.TaskPath + $t.TaskName + ' [' + $t.State + ']') }
    foreach ($st in @($Startup | Where-Object { ([string]$_.Name + ' ' + [string]$_.Command) -match $Pat })) { Flag ('VPN/proxy/DPI-type AUTOSTART entry: ' + (Cut $st.Name 40) + ' -> ' + (Cut $st.Command 100)) }
    $RpBefore = @($Rp | Where-Object { $_.ConvertToDateTime($_.CreationTime) -lt $SinceDate.AddDays(1) })
    if ($RpBefore.Count -gt 0) { $lastRp = $RpBefore[-1]; Flag ('System Restore point exists from ' + $lastRp.ConvertToDateTime($lastRp.CreationTime).ToString('yyyy-MM-dd HH:mm') + ' (before the agent day) -> LAST-RESORT rollback option.') }
    if ($OcHits.Count -gt 0) { Flag ('opencode history: ' + $OcHits.Count + ' system-changing command snippet(s) since ' + $SinceStr + ' -> READ out\opencode_history.txt') }
}

# ===================== report sections =====================
Add-Section $Report 'ADAPTERS (all visible)' {
    Tbl ($Adapters | Sort-Object Status, Name | Select-Object Name, @{n = 'Description'; e = { Cut $_.InterfaceDescription 45 } }, Status, LinkSpeed, MediaConnectionState, @{n = 'Media'; e = { $_.PhysicalMediaType } })
}
if (-not $Quick) {
    Add-Section $Report 'WIRED ADAPTER: driver, device problems, advanced settings, power' {
        Tbl ($Wired | Select-Object Name, Status, DriverProvider, DriverVersion, DriverDate, @{n = 'DriverFile'; e = { $_.DriverFileName } })
        'Device Manager network devices (PCI/USB):'
        Tbl (@(foreach ($d in $PnpNet) {
            $pc = $null
            try { $pc = (Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName 'DEVPKEY_Device_ProblemCode' -ErrorAction Stop).Data } catch { }
            [pscustomobject]@{ Status = [string]$d.Status; Present = $d.Present; Problem = $pc; Name = (Cut $d.FriendlyName 55) }
        }))
        'Present PCI/USB devices with problems (any class):'
        Tbl ($PnpBadInfo | Select-Object -First 10 -Property Name, Class, Status, Problem, NetDevice)
        foreach ($a in $Wired) {
            ('Advanced properties of ' + $a.Name + ':')
            Tbl (Get-NetAdapterAdvancedProperty -Name $a.Name -ErrorAction SilentlyContinue | Select-Object -First 30 -Property @{n = 'Setting'; e = { Cut $_.DisplayName 40 } }, @{n = 'Value'; e = { Cut $_.DisplayValue 30 } })
            ('Power management of ' + $a.Name + ':')
            Tbl (Get-NetAdapterPowerManagement -Name $a.Name -ErrorAction SilentlyContinue | Select-Object AllowComputerToTurnOffDevice, DeviceSleepOnDisconnect, SelectiveSuspend)
        }
    }
    Add-Section $Report 'BINDINGS on wired adapter(s): IPv4/IPv6 + all non-Microsoft components' {
        Tbl ($WiredBind | Where-Object { @('ms_tcpip', 'ms_tcpip6') -contains [string]$_.ComponentID -or [string]$_.ComponentID -notmatch '^ms_' } | Select-Object Name, DisplayName, ComponentID, Enabled)
    }
}
Add-Section $Report 'IPV4 CONFIG' {
    Tbl ($IPv4 | Where-Object { [string]$_.IPAddress -ne '127.0.0.1' } | Select-Object InterfaceAlias, IPAddress, PrefixLength, PrefixOrigin, AddressState)
    Tbl ($IfV4 | Where-Object { [string]$_.ConnectionState -eq 'Connected' -and [string]$_.InterfaceAlias -notlike 'Loopback*' } | Select-Object InterfaceAlias, Dhcp, InterfaceMetric, NlMtu)
}
Add-Section $Report 'ROUTES (default-type + persistent)' {
    Tbl ($DefRoutes | Select-Object InterfaceAlias, DestinationPrefix, NextHop, RouteMetric)
    'Persistent routes:'
    Tbl ($PersRoutes | Select-Object DestinationPrefix, NextHop, InterfaceAlias, RouteMetric)
}
Add-Section $Report 'DNS' {
    Tbl ($DnsSrv | Where-Object { $UpIdx -contains $_.InterfaceIndex } | Select-Object InterfaceAlias, @{n = 'Family'; e = { if ([string]$_.AddressFamily -match '^(2|IPv4)$') { 'IPv4' } else { 'IPv6' } } }, @{n = 'Servers'; e = { $_.ServerAddresses -join ', ' } })
    foreach ($a in $Wired) {
        $tp = Try-Get { Get-ItemProperty -Path ('HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\' + $a.InterfaceGuid) -ErrorAction Stop }
        if ($tp) { [string]$a.Name + ': static NameServer=[' + $tp.NameServer + '] DhcpNameServer=[' + $tp.DhcpNameServer + '] EnableDHCP=' + $tp.EnableDHCP }
    }
    'NRPT rules:'
    Tbl ($Nrpt | Select-Object -First 10 -Property Namespace, @{n = 'NameServers'; e = { $_.NameServers -join ',' } }, DisplayName)
    'DoH servers (Windows 11):'
    Tbl (Try-Get { Get-DnsClientDohServerAddress -ErrorAction Stop | Select-Object -First 10 -Property ServerAddress, DohTemplate, AutoUpgrade })
    ('hosts file, active lines (' + $HostsActive.Count + '):')
    @($HostsActive | Select-Object -First 25 | ForEach-Object { Cut $_ 120 })
    'UDP 53 listeners:'
    Tbl ($Udp53 | Select-Object LocalAddress, LocalPort, @{n = 'Process'; e = { Get-ProcName $_.OwningProcess } })
}
Add-Section $Report 'PROXY' {
    $ovr = ''
    $adt = ''
    if ($Inet) { $ovr = Cut $Inet.ProxyOverride 80; $adt = [string]$Inet.AutoDetect }
    ('WinINET (HKCU, used by browsers): ProxyEnable=' + $ProxyEnable + ' ProxyServer=[' + $ProxyServer + '] AutoConfigURL=[' + $PacUrl + '] ProxyOverride=[' + $ovr + '] AutoDetect=' + $adt)
    $pol = Try-Get { Get-ItemProperty -Path 'HKLM:\Software\Policies\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction Stop }
    if ($pol) { 'Policy (HKLM): ProxySettingsPerUser=' + $pol.ProxySettingsPerUser }
    ('WinHTTP (used by services): ' + (Cut $WinHttp 200))
    'Proxy environment variables:'
    if ($EnvProxies.Count -gt 0) { $EnvProxies } else { '(none)' }
    'Tool configs mentioning proxy (pip/npm/git):'
    foreach ($cf in @((Join-Path $env:APPDATA 'pip\pip.ini'), (Join-Path $env:USERPROFILE 'pip\pip.ini'), (Join-Path $env:USERPROFILE '.npmrc'), (Join-Path $env:USERPROFILE '.gitconfig'))) {
        if (Test-Path -LiteralPath $cf) { Select-String -LiteralPath $cf -Pattern 'proxy' -ErrorAction SilentlyContinue | ForEach-Object { $cf + ': ' + (Cut $_.Line 100) } }
    }
    'Listening TCP ports of non-system processes (local proxies / VPN cores show up here):'
    Tbl ($Listen | Where-Object { @('127.0.0.1', '::1', '0.0.0.0', '::') -contains [string]$_.LocalAddress } | ForEach-Object { [pscustomobject]@{ Port = $_.LocalPort; Address = [string]$_.LocalAddress; Process = (Get-ProcName $_.OwningProcess) } } | Where-Object { @('svchost', 'System', 'lsass', 'wininit', 'services', 'spoolsv', 'Idle', '?') -notcontains $_.Process } | Sort-Object Port -Unique | Select-Object -First 25)
}
if (-not $Quick) {
    Add-Section $Report 'VPN / PROXY / DPI-BYPASS / VIRTUAL NETWORK' {
        'Virtual (non-physical) adapters:'
        Tbl ($Adapters | Where-Object { $PhysIdx -notcontains $_.ifIndex } | Select-Object Name, @{n = 'Description'; e = { Cut $_.InterfaceDescription 50 } }, Status)
        'Services:'
        Tbl ($SvcHit | Select-Object Name, State, StartMode, @{n = 'Path'; e = { Cut $_.PathName 90 } })
        'Drivers:'
        Tbl ($DrvHit | Select-Object Name, State, StartMode, @{n = 'Path'; e = { Cut $_.PathName 90 } })
        'Processes:'
        Tbl ($ProcHit | Select-Object ProcessName, Id, @{n = 'Path'; e = { Cut $_.Path 90 } })
        'Scheduled tasks:'
        Tbl ($TaskHit | Select-Object -First 15 -Property TaskName, State, @{n = 'Action'; e = { Cut ((@($_.Actions) | ForEach-Object { [string]$_.Execute + ' ' + [string]$_.Arguments }) -join ' ; ') 90 } })
        'Autostart entries (all):'
        Tbl ($Startup | Select-Object -First 25 -Property @{n = 'Name'; e = { Cut $_.Name 30 } }, @{n = 'Command'; e = { Cut $_.Command 100 } })
        'Hyper-V switches:'
        Tbl ($VmSw | Select-Object Name, SwitchType, NetAdapterInterfaceDescription)
    }
    Add-Section $Report 'FIREWALL' {
        Tbl ($FwProf | Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction)
        ('Enabled OUTBOUND BLOCK rules (' + $FwOutBlock.Count + '):')
        Tbl ($FwOutBlock | Select-Object -First 20 -Property @{n = 'DisplayName'; e = { Cut $_.DisplayName 60 } }, @{n = 'Name'; e = { Cut $_.Name 40 } }, Profile)
        'Third-party firewall / security services:'
        Tbl ($SvcAll | Where-Object { ([string]$_.Name + ' ' + [string]$_.DisplayName + ' ' + [string]$_.PathName) -match 'simplewall|portmaster|safing|tinywall|glasswire|firewall control|comodo|outpost|\beset\b|kaspersky|avast|\bavg\b|bitdefender|adguard|dr\.?web' } | Select-Object Name, State, StartMode)
        'WFP filters, most frequent names (admin only):'
        if ($WfpTop) { Tbl $WfpTop } else { '(not collected: needs Administrator, or -Quick mode)' }
        if ($WfpHit.Count -gt 0) { 'WFP filters with VPN/DPI-type names:'; @($WfpHit | Select-Object -First 15) }
    }
    Add-Section $Report 'WINSOCK CATALOG (provider DLLs)' {
        if ($WsDlls.Count -gt 0) { $WsDlls } else { '(could not read)' }
    }
    Add-Section $Report 'CORE NETWORK SERVICES / DRIVERS' {
        Tbl ($SvcAll | Where-Object { @('Dhcp', 'Dnscache', 'nsi', 'BFE', 'MpsSvc', 'NlaSvc', 'netprofm', 'Wcmsvc', 'WinHttpAutoProxySvc', 'iphlpsvc', 'Netman', 'NcbService') -contains [string]$_.Name } | Select-Object Name, State, StartMode)
        Tbl ($DrvAll | Where-Object { @('AFD', 'Tcpip', 'NDIS', 'WinDivert', 'WinDivert14', 'wintun', 'tap0901', 'npcap', 'npf') -contains [string]$_.Name } | Select-Object Name, State, StartMode)
    }
    Add-Section $Report 'NCSI (logic behind the tray "No Internet" icon)' {
        if ($Ncsi) { 'EnableActiveProbing=' + $Ncsi.EnableActiveProbing + ' ActiveWebProbeHost=' + $Ncsi.ActiveWebProbeHost + ' ActiveDnsProbeHost=' + $Ncsi.ActiveDnsProbeHost } else { '(not readable)' }
    }

    # ----- changes.txt sections -----
    Add-Section $Changes ('SERVICES / DRIVERS INSTALLED since ' + $SinceStr + ' (System event 7045)') {
        @($Ev7045 | Select-Object -First 30 | ForEach-Object { $_.TimeCreated.ToString('MM-dd HH:mm') + ' | ' + [string]$_.Properties[0].Value + ' | ' + (Cut ([string]$_.Properties[1].Value) 90) + ' | start=' + [string]$_.Properties[3].Value })
    }
    Add-Section $Changes ('SERVICE START TYPE CHANGES since ' + $SinceStr + ' (event 7040, update noise removed)') {
        @($Ev7040Rel | Select-Object -First 20 | ForEach-Object { $_.TimeCreated.ToString('MM-dd HH:mm') + ' | ' + [string]$_.Properties[0].Value + ' | ' + [string]$_.Properties[1].Value + ' -> ' + [string]$_.Properties[2].Value + ' | ' + [string]$_.Properties[3].Value })
    }
    Add-Section $Changes ('MSI INSTALL / UNINSTALL since ' + $SinceStr) {
        @($EvMsi | Select-Object -First 25 | ForEach-Object { $_.TimeCreated.ToString('MM-dd HH:mm') + ' | id ' + $_.Id + ' | ' + (Cut ([string]$_.Properties[0].Value) 100) })
    }
    Add-Section $Changes ('PROGRAMS with InstallDate >= ' + $SinceStr) {
        Tbl ($NewApps | Sort-Object InstallDate | Select-Object -First 25 -Property @{n = 'Name'; e = { Cut $_.DisplayName 50 } }, DisplayVersion, InstallDate, @{n = 'Publisher'; e = { Cut $_.Publisher 30 } })
    }
    Add-Section $Changes ('NEW FOLDERS created since ' + $SinceStr + ' (Program Files, ProgramData, AppData, profile, Downloads, Desktop, C:\)') {
        Tbl ($NewDirs | Sort-Object CreationTime | Select-Object -Last 40 -Property @{n = 'Created'; e = { $_.CreationTime.ToString('MM-dd HH:mm') } }, FullName)
        'New files in Downloads:'
        Tbl ($NewDl | Sort-Object CreationTime | Select-Object -Last 15 -Property @{n = 'Created'; e = { $_.CreationTime.ToString('MM-dd HH:mm') } }, Name, Length)
    }
    Add-Section $Changes ('WINDOWS UPDATES installed since ' + $SinceStr) {
        Tbl ($Hotfix | Select-Object HotFixID, Description, InstalledOn)
    }
    Add-Section $Changes ('DRIVER INSTALLS since ' + $SinceStr + ' (setupapi.dev.log)') {
        @($DrvInst)
    }
    Add-Section $Changes ('SYSTEM LOG warnings/errors since ' + $SinceStr + ': top sources') {
        Tbl ($SysErr | Group-Object ProviderName | Sort-Object Count -Descending | Select-Object -First 12 -Property Count, Name)
    }
    Add-Section $Changes 'SYSTEM LOG: network-related warnings/errors (newest 20)' {
        @($SysErr | Where-Object { [string]$_.ProviderName -match 'Dhcp|Tcpip|NDIS|NetAdapter|Netwtw|e1[a-z]|rt[0-9a-z]*64|Realtek|Intel|Killer|DNS|NlaSvc|NCSI|WFP|BFE|Firewall|Service Control Manager|Kernel-PnP|iphlpsvc|Wcmsvc|WinDivert|Wintun|Tap' } | Select-Object -First 20 | ForEach-Object { $_.TimeCreated.ToString('MM-dd HH:mm') + ' | ' + $_.ProviderName + ' ' + $_.Id + ' | ' + (Cut $_.Message 140) })
    }
    Add-Section $Changes 'RESTORE POINTS (System Restore)' {
        if ($Rp.Count -eq 0) { '(none found: System Protection off, not Administrator, or not Windows PowerShell 5.1)' }
        else { @($Rp | Select-Object -Last 10 | ForEach-Object { '#' + $_.SequenceNumber + ' | ' + $_.ConvertToDateTime($_.CreationTime).ToString('yyyy-MM-dd HH:mm') + ' | ' + (Cut $_.Description 80) }) }
    }
    Add-Section $Changes ('OPENCODE HISTORY: system-changing commands in files modified since ' + $SinceStr) {
        ('Files scanned: ' + $OcScanned + '. Unique snippets: ' + $OcHits.Count + '. Full list: out\opencode_history.txt')
        if ($OcScanned -eq 0) { 'No opencode files found in: ' + ($OcDirs -join ' ; ') }
        @($OcHits | Select-Object -First 40)
    }
}

# ===================== write files =====================
$osText = ''
if ($Os) { $osText = [string]$Os.Caption + ' ' + [string]$Os.Version + ' | last boot ' + [string]$Os.LastBootUpTime }
$FlagLines = New-Object System.Collections.Generic.List[string]
$FlagLines.Add('===== RED FLAGS (' + $Flags.Count + ') =====')
if ($Flags.Count -eq 0) { $FlagLines.Add('(nothing detected automatically - read the LADDER and the details)') }
$fi = 0
foreach ($fl in $Flags) { $fi++; $FlagLines.Add('[' + $fi + '] ' + $fl) }

$Out = New-Object System.Collections.Generic.List[string]
$Out.Add('##### NETFIX DIAG REPORT (' + $Mode + ') #####')
$Out.Add('Generated: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' | Since: ' + $SinceStr + ' | Admin: ' + $IsAdmin + ' | PowerShell ' + [string]$PSVersionTable.PSVersion)
$Out.Add('OS: ' + $osText)
$Out.Add('This script is read-only. RED FLAGS are automatic hints - confirm them before acting.')
$Out.Add('')
foreach ($x in $FlagLines) { $Out.Add($x) }
$Out.Add('')
$Out.Add('===== LADDER (bottom-up connectivity tests) =====')
foreach ($x in $LadderLines) { $Out.Add($x) }
foreach ($x in $Report) { $Out.Add($x) }

$ReportFile = Join-Path $OutDir 'report.txt'
if ($Quick) { $ReportFile = Join-Path $OutDir 'quick.txt' }
$Out | Out-File -FilePath $ReportFile -Encoding UTF8 -Width 400
if (-not $Quick) {
    $ch = New-Object System.Collections.Generic.List[string]
    $ch.Add('##### NETFIX: WHAT CHANGED since ' + $SinceStr + ' (generated ' + (Get-Date -Format 'yyyy-MM-dd HH:mm') + ') #####')
    foreach ($x in $Changes) { $ch.Add($x) }
    $ch | Out-File -FilePath (Join-Path $OutDir 'changes.txt') -Encoding UTF8 -Width 400
    $oc = New-Object System.Collections.Generic.List[string]
    $oc.Add('# system-changing commands found in opencode files modified since ' + $SinceStr + ' (files scanned: ' + $OcScanned + ')')
    foreach ($x in $OcHits) { $oc.Add($x) }
    $oc | Out-File -FilePath (Join-Path $OutDir 'opencode_history.txt') -Encoding UTF8 -Width 400
}

# ===================== console summary =====================
Write-Host ''
foreach ($x in $FlagLines) { Write-Host $x }
Write-Host ''
Write-Host '===== LADDER ====='
foreach ($x in $LadderLines) { Write-Host $x }
Write-Host ''
Write-Host ('Saved: ' + $ReportFile)
if (-not $Quick) { Write-Host ('Saved: ' + (Join-Path $OutDir 'changes.txt') + ' and ' + (Join-Path $OutDir 'opencode_history.txt')) }
