$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$benchmarkPath = Join-Path $projectRoot "evaluation\questions.json"
$pdfDirectory = Join-Path $projectRoot "evaluation\raw"
$benchmark = Get-Content -LiteralPath $benchmarkPath -Raw | ConvertFrom-Json

New-Item -ItemType Directory -Path $pdfDirectory -Force | Out-Null

foreach ($document in $benchmark.corpus) {
    $destination = Join-Path $pdfDirectory $document.filename
    Invoke-WebRequest -Uri $document.url -OutFile $destination

    $stream = [System.IO.File]::OpenRead($destination)
    try {
        $signature = New-Object byte[] 5
        $bytesRead = $stream.Read($signature, 0, $signature.Length)
    }
    finally {
        $stream.Dispose()
    }

    if ($bytesRead -ne 5 -or [System.Text.Encoding]::ASCII.GetString($signature) -ne "%PDF-") {
        throw "Downloaded corpus file is not a PDF: $destination"
    }

    Write-Output "Downloaded $($document.title) to $destination"
}
