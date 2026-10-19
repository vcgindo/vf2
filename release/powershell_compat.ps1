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
