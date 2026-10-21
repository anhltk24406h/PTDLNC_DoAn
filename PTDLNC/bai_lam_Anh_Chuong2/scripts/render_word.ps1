$ErrorActionPreference = 'Stop'
$reportDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'report'
$docPath = (Resolve-Path -LiteralPath (Join-Path $reportDir 'Chuong_2.docx')).Path
$pdfPath = Join-Path $reportDir 'Chuong_2.pdf'
$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($docPath, $false, $true)
    $doc.Repaginate()
    Write-Output ('PAGES ' + $doc.ComputeStatistics(2))
    $doc.ExportAsFixedFormat($pdfPath, 17)
    Write-Output ('PDF ' + $pdfPath)
} finally {
    if ($null -ne $doc) { try { $doc.Close(0) } catch { Write-Warning 'Document already closed.' } }
    if ($null -ne $word) { try { $word.Quit() } catch { Write-Warning 'Word COM session already ended.' } }
}
