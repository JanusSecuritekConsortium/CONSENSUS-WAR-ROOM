# Opens Msty Go > Settings > Tools through Windows UI Automation, then returns to the app.
# Msty Go's Built-in Server may not listen after Msty Go starts until that page is shown.
# Prints one line: opened, no_window or not_found:<step>. Never reads or prints a token.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$A = [System.Windows.Automation.AutomationElement]
$process = Get-Process MstyGo -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $process) { 'no_window'; exit 0 }
$root = $A::FromHandle($process.MainWindowHandle)

function Find-Button($name) {
    $condition = New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, $name)
    # Chromium builds its accessibility tree after the first query, so retry briefly.
    foreach ($attempt in 1..10) {
        $button = $root.FindAll('Descendants', $condition) |
            Where-Object { $_.Current.ControlType.ProgrammaticName -in 'ControlType.Button', 'ControlType.MenuItem' } |
            Select-Object -First 1
        if ($button) { return $button }
        Start-Sleep -Milliseconds 500
    }
}

function Press($name) {
    $button = Find-Button $name
    if (-not $button) { "not_found:$name"; exit 0 }
    # Menu buttons expose Expand rather than Invoke.
    $pattern = $null
    if ($button.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) { $pattern.Invoke() }
    elseif ($button.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern, [ref]$pattern)) { $pattern.Expand() }
    else { "not_found:$name"; exit 0 }
    Start-Sleep -Milliseconds 800
}

if (-not (Find-Button 'Back to app')) {
    # The account menu may already be open from an earlier attempt.
    $condition = New-Object System.Windows.Automation.PropertyCondition($A::NameProperty, 'Settings')
    $menuOpen = $root.FindAll('Descendants', $condition) | Where-Object { $_.Current.ControlType.ProgrammaticName -eq 'ControlType.MenuItem' }
    if (-not $menuOpen) { Press 'Msty Account menu' }
    Press 'Settings'
}
Press 'Tools'
Start-Sleep -Seconds 3
Press 'Back to app'
'opened'
