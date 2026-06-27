# Tools

## PowerShell

- Purpose: parse and runtime verification of the portable `.ps1` bootstrap,
  global-agent setup, and scoped-agent setup scripts.
- Installation: `brew install powershell`.
- Installed version: PowerShell `7.6.3`.
- Installed dependency: .NET `10.0.301`.
- Version check: `pwsh --version`.
- Parser check: use
  `[System.Management.Automation.Language.Parser]::ParseFile()` for every
  script in `scripts/`.
- Runtime coverage: macOS ARM64 with PowerShell 7.6.3.
- Remaining coverage gap: Windows PowerShell 5.1 has not been executed on the
  current machine; scripts retain UTF-8-without-BOM helpers compatible with
  that environment.

Project automation should continue to use dependency-free shell and PowerShell
entry points for clean-machine compatibility. Python 3 standard-library code is
preferred when future cross-platform logic becomes complex enough to justify a
shared implementation and Python availability is confirmed on every target.
