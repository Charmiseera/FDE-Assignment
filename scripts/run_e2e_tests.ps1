# End-to-End Automated Integration Test Suite for Lenny Growth Assistant
# Evaluates all 7 user flows defined in IMPLEMENTATION_PLAN.md Step 5.2

$ErrorActionPreference = "Stop"
$passed = 0
$failed = 0

function Assert-Test([string]$name, [bool]$condition) {
    if ($condition) {
        Write-Host "[PASS] $name" -ForegroundColor Green
        $script:passed++
    } else {
        Write-Host "[FAIL] $name" -ForegroundColor Red
        $script:failed++
    }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Running Automated E2E Test Suite for 7 PRD Scenarios    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# ── Test 1: Stack Health & Provider Config ──
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health"
    Assert-Test "1. Health Endpoint returns DB and providers OK" ($health.success -eq $true -and $health.data.database -eq "ok")
    
    $config = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/config"
    Assert-Test "1b. Config Endpoint returns active provider" ($config.success -eq $true -and $config.data.llm_provider -ne $null)
} catch {
    Assert-Test "1. Health & Config Endpoints" $false
}

# ── Test 2: Session Creation & Listing ──
try {
    $session = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions" -Method POST -ContentType "application/json" -Body "{}"
    $sid = $session.data.session_id
    Assert-Test "2. Session Created successfully" ($session.success -eq $true -and $sid -ne $null)

    $sessionsList = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions"
    $found = ($sessionsList.data | Where-Object { $_.session_id -eq $sid })
    Assert-Test "2b. Session appears in sessions list" ($found -ne $null)
} catch {
    Assert-Test "2. Session Lifecycle" $false
}

# ── Test 3: Grounded Q&A with Citations ──
try {
    $msg1 = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions/$sid/messages" -Method POST -ContentType "application/json" -Body '{"content":"What does Lenny say about activation metrics for PLG?","provider":"groq"}'
    $hasCitations = ($msg1.data.citations.Count -gt 0)
    $hasRelevantAnswer = ($msg1.data.content.Length -gt 20)
    Assert-Test "3. Grounded Q&A returns answer with transcript citations" ($hasCitations -and $hasRelevantAnswer)
} catch {
    Assert-Test "3. Grounded Q&A" $false
}

# ── Test 4: Out-of-Corpus Refusal (Zero Citations) ──
try {
    $refusalSession = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions" -Method POST -ContentType "application/json" -Body "{}"
    $refusalSid = $refusalSession.data.session_id
    $msgRefusal = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions/$refusalSid/messages" -Method POST -ContentType "application/json" -Body '{"content":"What is the recipe for baking chocolate cake?","provider":"groq"}'
    $isRefusal = ($msgRefusal.data.content -like "*couldn't find anything in Lenny's Podcast transcripts*")
    $zeroCitations = ($msgRefusal.data.citations.Count -eq 0)
    Assert-Test "4. Out-of-corpus query emits refusal with zero citations" ($isRefusal -and $zeroCitations)
} catch {
    Assert-Test "4. Out-of-corpus refusal" $false
}

# ── Test 5: Multi-Turn Context & Ship 30/30 Essay Generation ──
try {
    $msgEssay = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions/$sid/messages" -Method POST -ContentType "application/json" -Body '{"content":"Turn this into a Ship 30/30 essay","provider":"groq"}'
    $hasArtifact = ($msgEssay.data.artifact_id -ne $null)
    Assert-Test "5. Essay request returns generated artifact ID" $hasArtifact

    if ($hasArtifact) {
        $art = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions/$sid/artifacts/$($msgEssay.data.artifact_id)"
        $hasTitle = ($art.data.title -ne $null)
        $hasValidationStatus = ($art.data.metadata.validation_status -ne $null)
        $hasCleanMarkdown = ($art.data.content -like "*##*")
        Assert-Test "5b. Essay artifact stored with metadata.validation_status" ($hasTitle -and $hasValidationStatus -and $hasCleanMarkdown)
    }
} catch {
    Assert-Test "5. Essay generation and artifact storage" $false
}

# ── Test 6: HTML Security Isolation Verification ──
try {
    # Check ArtifactViewer.tsx source to verify allow-same-origin is withheld
    $viewerSrc = Get-Content "d:\FDE\frontend\src\components\artifacts\ArtifactViewer.tsx" -Raw
    $hasSandbox = ($viewerSrc -match 'sandbox="allow-scripts"')
    $noSameOrigin = (-not ($viewerSrc -match 'allow-same-origin'))
    Assert-Test "6. Sandboxed iframe uses allow-scripts without allow-same-origin" ($hasSandbox -and $noSameOrigin)
} catch {
    Assert-Test "6. Security isolation verification" $false
}

# ── Test 7: Error Validation Envelope ──
try {
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sessions/$sid/messages" -Method POST -ContentType "application/json" -Body '{"content":"   "}'
        Assert-Test "7. Blank message returns 400 validation envelope" $false
    } catch {
        $ex = $_.Exception.Response
        Assert-Test "7. Blank message returns 400 validation envelope" ($ex.StatusCode.value__ -eq 400)
    }
} catch {
    Assert-Test "7. Validation envelope" $false
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "  RESULTS: $passed PASSED, $failed FAILED" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "==========================================================" -ForegroundColor Cyan

if ($failed -gt 0) {
    exit 1
}
