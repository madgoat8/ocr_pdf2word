$PYTHON = ".\python-3.11.5-embed-amd64\python.exe"
$CONFIG = "src\config.yaml"
$INPUT_DIR = "input"

$pdfs = Get-ChildItem "$INPUT_DIR\*.pdf"
if (-not $pdfs) {
    Write-Host "[ERROR] No PDF files found in $INPUT_DIR/"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "========================================"
Write-Host " Batch PDF -> Word Conversion"
Write-Host " Found $($pdfs.Count) PDF(s)"
Write-Host "========================================"
Write-Host ""

New-Item "output" -ItemType Directory -Force | Out-Null

foreach ($pdf in $pdfs) {
    $outName = "$($pdf.BaseName)_ocr.docx"
    $outPath = Join-Path "output" $outName
    Write-Host ">>> Processing: $($pdf.Name)"
    Write-Host "    Output: $outPath"
    Write-Host ""
    & $PYTHON src/main.py $pdf.FullName -c $CONFIG -o $outPath
    Write-Host "----------------------------------------"
    Write-Host ""
}

Write-Host "========================================"
Write-Host " All done! Output files in output\"
Write-Host "========================================"
Read-Host "Press Enter to exit"
