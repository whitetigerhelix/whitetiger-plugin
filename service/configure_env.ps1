param(
    [ValidateSet("azure", "anthropic")]
    [string]$Provider,

    [string]$AzureEndpoint,
    [string]$AzureApiKey,
    [string]$AzureDeployment,
    [string]$AzureApiVersion,

    [string]$AnthropicApiKey,
    [string]$AnthropicModel,

    [int]$ServicePort,
    [int]$LlmTimeoutSeconds,

    [switch]$UseMock,
    [switch]$UseReal,

    [switch]$Show
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($UseMock -and $UseReal) {
    throw "Choose only one of -UseMock or -UseReal."
}

function Update-OrAppend {
    param(
        [string]$Content,
        [string]$Key,
        [string]$Value
    )

    $pattern = "(?m)^" + [regex]::Escape($Key) + "=.*$"

    if ([regex]::IsMatch($Content, $pattern)) {
        return [regex]::Replace($Content, $pattern, { param($m) "$Key=$Value" }, 1)
    }

    $trimmed = $Content.TrimEnd("`r", "`n")
    if ($trimmed.Length -eq 0) {
        return "$Key=$Value`r`n"
    }

    return "$trimmed`r`n$Key=$Value`r`n"
}

function Mask-If-Secret {
    param(
        [string]$Key,
        [string]$Value
    )

    if ($Key -match "API_KEY|KEY") {
        if ([string]::IsNullOrWhiteSpace($Value)) {
            return ""
        }
        if ($Value.Length -le 6) {
            return "******"
        }
        return ($Value.Substring(0, 3) + "..." + $Value.Substring($Value.Length - 2))
    }

    return $Value
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $scriptDir ".env"
$envExamplePath = Join-Path $scriptDir ".env.example"

if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
    } else {
        New-Item -Path $envPath -ItemType File | Out-Null
    }
}

$content = Get-Content $envPath -Raw

$updates = [ordered]@{}

if ($Provider) { $updates["LLM_PROVIDER"] = $Provider }
if ($AzureEndpoint) { $updates["AZURE_OPENAI_ENDPOINT"] = $AzureEndpoint }
if ($AzureApiKey) { $updates["AZURE_OPENAI_API_KEY"] = $AzureApiKey }
if ($AzureDeployment) { $updates["AZURE_OPENAI_DEPLOYMENT"] = $AzureDeployment }
if ($AzureApiVersion) { $updates["AZURE_OPENAI_API_VERSION"] = $AzureApiVersion }

if ($AnthropicApiKey) { $updates["ANTHROPIC_API_KEY"] = $AnthropicApiKey }
if ($AnthropicModel) { $updates["ANTHROPIC_MODEL"] = $AnthropicModel }

if ($ServicePort -gt 0) { $updates["SERVICE_PORT"] = [string]$ServicePort }
if ($LlmTimeoutSeconds -gt 0) { $updates["LLM_TIMEOUT_SECONDS"] = [string]$LlmTimeoutSeconds }

if ($UseMock) { $updates["SERVICE_MOCK"] = "1" }
if ($UseReal) { $updates["SERVICE_MOCK"] = "0" }

if ($updates.Count -eq 0) {
    Write-Host "No updates requested. Use parameters to set values."
} else {
    foreach ($entry in $updates.GetEnumerator()) {
        $content = Update-OrAppend -Content $content -Key $entry.Key -Value $entry.Value
    }

    Set-Content -Path $envPath -Value $content -Encoding UTF8

    Write-Host "Updated .env values:"
    foreach ($entry in $updates.GetEnumerator()) {
        $displayValue = Mask-If-Secret -Key $entry.Key -Value ([string]$entry.Value)
        Write-Host "  $($entry.Key)=$displayValue"
    }
}

if ($Show) {
    Write-Host ""
    Write-Host "Current key settings:"
    $raw = Get-Content $envPath
    foreach ($line in $raw) {
        if ($line -match "^\s*#" -or $line -notmatch "=") {
            continue
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0]
        $val = if ($parts.Length -gt 1) { $parts[1] } else { "" }
        $safe = Mask-If-Secret -Key $key -Value $val
        Write-Host "  $key=$safe"
    }
}
