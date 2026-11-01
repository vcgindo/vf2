# Shared host compatibility for Windows PowerShell 5.1 and PowerShell 7.
# DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
function ConvertFrom-VfJson([string]$Text) {
    function ConvertValue($Value) {
        if ($null -eq $Value) { return $null }
        if ($Value -is [System.Management.Automation.PSCustomObject]) {
            $result = @{}
            foreach ($property in $Value.PSObject.Properties) { $result[$property.Name] = ConvertValue $property.Value }
            return $result
        }
        if ($Value -is [array]) {
            $items = New-Object 'System.Collections.Generic.List[object]'
            foreach ($item in $Value) { $items.Add((ConvertValue $item)) }
            return ,$items.ToArray()
        }
        return $Value
    }
    return ConvertValue (ConvertFrom-Json -InputObject $Text)
}

function Test-VfAbsolutePath([string]$Path) {
    if ([IO.Path]::DirectorySeparatorChar -eq '\') {
        # IsPathRooted alone also accepts drive-relative C:foo and root-relative \foo.
        return $Path -match '^(?:[A-Za-z]:[\\/]|[\\/]{2}[^\\/]+[\\/][^\\/]+(?:[\\/]|$))'
    }
    return $Path.StartsWith('/')
}

function Resolve-VfProjectPath([string]$Root, [string]$Path) {
    if (-not $Path) { throw 'Configure a nonempty data path' }
    if (-not (Test-VfAbsolutePath $Path)) {
        # Reject ambiguous Windows drive/root-relative forms instead of adopting
        # the shell's current drive. Ordinary relative paths belong to the clone.
        if ([IO.Path]::IsPathRooted($Path) -or $Path -match '^[A-Za-z]:') {
            throw 'Use a fully qualified or project-relative data path'
        }
        $Path = Join-Path $Root $Path
    }
    return [IO.Path]::GetFullPath($Path)
}

function Get-VfRelativePath([string]$Root, [string]$Path) {
    $base = [IO.Path]::GetFullPath($Root).TrimEnd([char[]]'\/')
    $target = [IO.Path]::GetFullPath($Path)
    $comparison = if ([IO.Path]::DirectorySeparatorChar -eq '\') { [StringComparison]::OrdinalIgnoreCase } else { [StringComparison]::Ordinal }
    if ($target.Equals($base, $comparison)) { return '.' }
    $prefix = $base + [IO.Path]::DirectorySeparatorChar
    if (-not $target.StartsWith($prefix, $comparison)) { throw 'Input directory must stay inside VF_DAILY_INPUT_DIR' }
    return $target.Substring($prefix.Length).Replace('\','/')
}

function Write-VfUtf8([string]$Path, [string]$Text) {
    # Windows PowerShell's -Encoding utf8 adds a BOM. Native Python JSON reads
    # and the checksummed binding contract require UTF-8 without that prefix.
    [IO.File]::WriteAllText($Path, $Text, [Text.UTF8Encoding]::new($false))
}

function Set-VfProcessArguments($StartInfo, [string[]]$Values) {
    if ($null -ne $StartInfo.PSObject.Properties['ArgumentList']) {
        foreach ($value in $Values) { $StartInfo.ArgumentList.Add($value) }
    } else {
        # .NET Framework has Arguments only. Quote using Windows argv rules,
        # including JSON quotes, empty strings and trailing backslashes.
        $quoted = foreach ($value in $Values) {
            '"' + [regex]::Replace([regex]::Replace($value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
        }
        $StartInfo.Arguments = $quoted -join ' '
    }
}

function Write-VfEnvironment([string]$Root, [hashtable]$Changes) {
    $path = Join-Path $Root '.env'
    $text = [IO.File]::ReadAllText($path)
    foreach ($Name in $Changes.Keys) {
        $Value = [string]$Changes[$Name]
        if ($Value -match '[\r\n"$`]') { throw "Unsupported characters in $Name" }
        $pattern = '(?m)^\s*' + [regex]::Escape($Name) + '\s*=.*$'
        $line = $Name + '="' + $Value + '"'
        if ([regex]::IsMatch($text,$pattern)) { $text = [regex]::Replace($text,$pattern,[System.Text.RegularExpressions.MatchEvaluator]{param($m) $line}) }
        else { $text += "`n$line`n" }
    }
    $candidate = Join-Path $Root ('.env.csv-' + [guid]::NewGuid().ToString('N'))
    try {
        [IO.File]::WriteAllText($candidate,$text,[Text.UTF8Encoding]::new($false))
        $preference = $ErrorActionPreference
        try {
            # PS5 turns ordinary redirected native stderr into error records.
            # Docker's exit code, rather than progress output, decides failure.
            $ErrorActionPreference = 'Continue'
            $diagnostic = & docker compose --env-file $candidate config --quiet 2>&1
            $code = $LASTEXITCODE
        } finally { $ErrorActionPreference = $preference }
        if ($code -ne 0) { throw 'Generated CSV environment failed Compose validation; original .env is unchanged' }
        [IO.File]::Replace($candidate,$path,[NullString]::Value)
    } finally { Remove-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue }
}

function Assert-VfUpgradeIdle([string]$StateRoot) {
    $path=Join-Path $StateRoot 'upgrade.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return }
    $upgrade=ConvertFrom-VfJson ([IO.File]::ReadAllText($path))
    if ($upgrade.ContainsKey('maintenance') -and $upgrade.maintenance -eq $true) {
        throw 'Production upgrade maintenance is active. Preserve the journal and use ./vf.ps1 upgrade -Resume before daily/scoped work.'
    }
}
