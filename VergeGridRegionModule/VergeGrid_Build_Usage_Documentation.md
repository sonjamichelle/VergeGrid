
# VergeGrid Region Security & Trust Module — Build & Usage Documentation

## Overview
This guide explains how to **build, install, and use** the VergeGrid Region Security & Trust Module for OpenSimulator 0.9.3+.
It covers both Windows and Linux/Unix environments and ensures compatibility with Mono or .NET Framework 4.8.

---

## 1. Prerequisites

### OpenSimulator
- Version: **0.9.3 or newer**
- Must have `OpenSim.Framework.dll` and `OpenSim.Region.Framework.dll` accessible in `/bin`.

### System Requirements
| Requirement | Version | Purpose |
|--------------|----------|----------|
| Mono | 6.12+ | Linux/Unix runtime environment |
| .NET Framework | 4.8+ | Windows runtime compatibility |
| MySQL | 8.x+ | VergeGrid control plane database |
| Newtonsoft.Json | 13.0+ | JSON serialization |

---

## 2. Building the Module

### Linux / macOS

```bash
# Ensure dependencies are installed
sudo apt install mono-complete -y

# Clone or copy VergeGrid module
cd VergeGridRegionSecurity/

# Build module using Makefile
make build

# Optional: clean up build artifacts
make clean
```

Or directly via shell script:

```bash
./build.sh
```

This will:
- Compile the module via `msbuild`
- Auto-update the `AssemblyVersion` timestamp
- Copy the resulting DLL to your OpenSim `/bin/` folder

### Windows

```bat
REM Build the module using MSBuild
build.bat
```

This script will automatically copy the DLL into the OpenSim `/bin/` directory after a successful build.

---

## 3. Verifying the Build

After building, verify the output:

```
bin/Release/VergeGridRegionSecurity.dll
```

Ensure the following message appears in your build log:
```
[VergeGrid] Build completed successfully. Output: VergeGridRegionSecurity.dll
```

---

## 4. Installing the Module in OpenSimulator

1. Copy the `VergeGridRegionSecurity.dll` to your OpenSim installation folder:
   ```bash
   cp bin/Release/VergeGridRegionSecurity.dll /path/to/OpenSim/bin/
   ```

2. Open `OpenSim.ini` and add this line under `[Startup]`:
   ```ini
   [Startup]
   regionmodules=VergeGridRegionModule
   ```

3. Restart OpenSimulator. You should see:
   ```
   [VergeGrid] Initializing with automatic RSA key rotation and revocation...
   ```

---

## 5. Data Directory Structure

The module maintains its own `data/` folder for cryptographic and trust data.

```
data/
├── vergegrid_trust.enc       # AES-256 encrypted trust data
├── vergegrid_peer_key.pem    # RSA private key for peer signing
└── vergegrid_peer_meta.json  # Metadata for key creation & expiry
```

**Do not share or move these files** between nodes unless part of an authorized cluster configuration.

---

## 6. Running Tests

Use NUnit to run the included test suite.

### Linux / macOS
```bash
nunit-console Tests/bin/Release/VergeGridRegionSecurity.Tests.dll
```

### Windows (PowerShell)
```powershell
dotnet test VergeGridRegionSecurity.Tests.csproj
```

Expected output:
```
All tests passed (4 assertions)
```

---

## 7. Using VergeGrid at Runtime

Once loaded, VergeGrid will:
- Register the simulator with the control plane automatically.
- Establish encrypted communication channels.
- Sync trust and consensus data.
- Manage region lifecycle (create/delete on demand).

You can verify operation by monitoring console logs or querying:
```
http://localhost:8000/trust/status
```

---

## 8. Common Commands

| Command | Description |
|----------|--------------|
| `make build` | Builds the module |
| `make install` | Installs DLL to OpenSim/bin |
| `make clean` | Cleans compiled output |
| `./build.sh` | Linux/macOS auto-build script |
| `build.bat` | Windows auto-build script |

---

## 9. Troubleshooting

### Issue: Missing Newtonsoft.Json
- Ensure `Newtonsoft.Json.dll` exists in `OpenSim/bin/`.
- Download from NuGet if missing: https://www.nuget.org/packages/Newtonsoft.Json/

### Issue: RSA key not found
- Delete the `data/` folder and restart OpenSim — keys regenerate automatically.

### Issue: Module not loading
- Check `OpenSim.ini` → `regionmodules=VergeGridRegionModule`
- Confirm DLL is in the same directory as `OpenSim.exe`.

---

## 10. License
```
MIT License
Copyright (c) 2025 VergeGrid
```

---

## 11. Maintainers
- **VergeGrid Core Development Team**
- **Lead Maintainer:** PulsR | Code GPT
- **Email:** dev@vergegrid.io
