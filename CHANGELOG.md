# VergeGrid Modular Installer — CHANGELOG
All notable changes to the VergeGrid Modular Installer system are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.9.7] – 2025-11-18 06:49 UTC

### 🛠️ Changed
- Installer now hard-fails if Environment Manager is missing instead of skipping
- Added full process tree kill on user cancellation or failure
- Removed spurious `[WARN] Environment Manager not found` message

### 🧱 Internal Improvements
- Improved environment manager path detection
- Unified cancel/abort behavior across all VergeGrid installer phases

## [v0.9.5] – 2025-11-18 06:08 UTC

### 🛠️ Changed
- Installer now auto-detects Environment Manager location across setup hierarchy
- Fixed false "Environment Manager not found" warning
- Installer halts correctly when cleanup is cancelled by user

### 🧱 Internal Improvements
- Unified path resolution for setup utilities
- Hardened subprocess control and sentinel detection

## [v0.9.4] – 2025-11-18 05:52 UTC

### 🛠️ Changed
- Installer now properly detects and halts on user cancellation from Environment Manager
- Added pre-install Environment Manager integration phase
- Updated run_component() to respect sentinel `::VERGEGRID_CANCELLED::` and exit code 111

### 🧱 Internal Improvements
- Improved subprocess handling for safer cleanup and installation workflows
- Ensured consistent termination behavior across all VergeGrid installer modules

## [v0.9.3] – 2025-11-18 05:17 UTC

### Added
- Explicit cancel sentinel `::VERGEGRID_CANCELLED::` for installer subprocess detection
- Unique exit code `111` to signal user abort to parent process

### Fixed
- Prevented installer from continuing execution after user cancels Environment Manager
- Improved integration safety between cleanup and installer workflows


## [v0.9.3] – 2025-11-18 04:09
### 🚀 Added
- CHANGELOG version entry timestamp.

### 🛠️ Changed
- Changes this: ## [v0.X.X] - 2025-11-18  to this:  ## [v0.X.X] - 2025-11-18 2155

### 🧱 Internal Improvements
- more concise.


## [v0.9.2] – 2025-11-18
### 🚀 Added
- changed the script from a oneline entry into a prompt flow. Parses for last version, suggests new version, asks for description, then changes, then improvements.

### 🛠️ Changed
- Parses for last version, suggests new version, asks for description, then changes, then improvements.

### 🧱 Internal Improvements
- Less Guesswork. More passed on information. Less Copy/Paste to do.


## [v0.9.1] – 2025-11-18
### 🚀 Added
- Added bump-changelog.py script

### 🛠️ Changed
- 

### 🧱 Internal Improvements
- 


## [v0.9.0] – 2025-11-18
### 🚀 Added
- **Dynamic Installation Root Architecture**
  - All setup scripts now accept `<install_root>` via CLI arguments.
  - Fully supports installations on any drive and custom folder (e.g. `E:\GridOne`, `C:\Sandbox\VergeGrid`).
  - Introduced environment variable `VERGEGRID_INSTALL_ROOT` for cross-process consistency.
- **Unified Entry Point Standard**
  - All modules now share this entry structure:
    ```python
    if len(sys.argv) < 2:
        print("Usage: python <script>.py <install_root>")
        sys.exit(1)
    ```
  - Standardized startup banners, usage hints, and error handling.
- **Centralized Logging**
  - All components write to `<install_root>\Logs\vergegrid-install.log`.
  - Consistent per-install logging across MySQL, OpenSim, Apache, PHP, and SSL stages.
- **Finalized Step Order**
  - Reordered main installer to place **OpenSim as final setup phase**.
  - Added **Step 7: `verify-db-robust.py`** for post-install database and service verification.

### 🛠️ Changed
- Removed all hardcoded paths (`C:\VergeGrid`, `D:\VergeGrid`) from every module.
- Updated `select_install_drive()`:
  - Now prompts for drive and install directory name.
  - Automatically creates directories.
- Enhanced `run_component()` for cleaner exit and failure handling.
- Improved admin privilege check (auto elevation if not admin).
- Revised service creation in `init-opensim-services.py` for manual-start mode.
- Adjusted SSL scripts (`init-ssl-apache.py`, `init-ssl-opensim.py`) for dynamic paths and certificate discovery.

### 🧱 Internal Improvements
- Consistent exit codes (`sys.exit(0/1)`) in all components.
- Safe subprocess error handling and tracebacks for all init scripts.
- Improved MySQL initialization with automatic PyMySQL dependency resolution.
- Verified full cross-module compatibility under dynamic install roots.

### ✅ Verified Compatibility
- Works seamlessly under the main modular installer orchestrator:
  - `fetch-mysql.py`
  - `init-mysql.py`
  - `fetch-opensim.py`
  - `init-opensim.py`
  - `init-opensim-services.py`
  - `fetch-apache.py`
  - `fetch-php.py`
  - `init-apache-php.py`
  - `fetch-letsencrypt.py`
  - `init-ssl-apache.py`
  - `init-ssl-opensim.py`
  - `verify-db-robust.py`

---

## [v0.8.0] – 2025-10-14
### 🚀 Added
- **OpenSim & MySQL Integration**
  - Introduced `init-opensim.py` and `init-mysql.py` for automated fetch, extraction, and base configuration.
  - Added automated MySQL insecure initialization (no password) for dev environments.
- **Robust Service Registration**
  - Added `init-opensim-services.py` to create the `VergeGridRobust` Windows service.
  - Generates debug launcher batch file `launch_robust_debug.bat` for manual service runs.
- **INI Validation**
  - Checks existence and size of `Robust.ini` and `GridCommon.ini` before continuing setup.
  - Graceful failure and logging if configs are missing or malformed.

### 🧩 Changed
- Moved OpenSim initialization logic out of the MySQL phase for modular execution.
- Added `common.write_log()` wrapper for uniform logging.
- Extended `run_component()` to display output and capture return codes.

---

## [v0.7.0] – 2025-09-22
### 🚀 Added
- **Apache + PHP Stack Fetchers**
  - `fetch-apache.py` and `fetch-php.py` introduced to handle download and extraction.
  - `init-apache-php.py` added to link PHP with Apache automatically (mod_php or CGI mode).
- **SSL Integration Base**
  - Added `fetch-letsencrypt.py` to install and configure `win-acme` ACME client for Windows.
  - Stubbed `init-ssl-apache.py` and `init-ssl-opensim.py` for later enhancement.

### 🛠️ Changed
- Updated installer orchestration to include Apache and PHP after MySQL/OpenSim setup.
- Unified naming conventions across all setup modules.
- Centralized all fetcher logs under `<install_root>\Logs`.

---

## [v0.6.0] – 2025-09-10
### 🚀 Added
- **Initial Modular Installer Framework**
  - `vergegrid_installer.py` created as the top-level orchestrator.
  - Handles drive detection, selection, and confirmation prompts.
  - Modular sequencing for MySQL, OpenSim, Apache, PHP, and SSL.
- **Common Utilities Module (`common.py`)**
  - Added centralized logging, timestamped file creation, and error recording.
  - Helper functions `set_log_file()`, `write_log()`, and `confirm()`.
- **Admin Elevation**
  - Added Windows UAC check and auto elevation via `ctypes.windll.shell32.ShellExecuteW`.

### 🧩 Changed
- Introduced `run_component()` abstraction for subprocess-based modular execution.
- Standardized console messages for all installation steps.

---

## [v0.5.0] – 2025-08-25
### 🚀 Added
- **VergeGrid Windows Setup Architecture Inception**
  - Created project scaffolding and initial folder layout under `/setup/`.
  - Implemented path detection logic to locate VergeGrid root dynamically.
  - Initial fetcher scripts for MySQL and OpenSim modules.
  - Introduced logging and version banners for modular install flow.

---

## [Unreleased]
### Planned
- Add secure password handling via `secure-mysql.py`.
- Introduce silent installer flag for non-interactive deployment.
- Per-component log separation in `/Logs/components/`.
- Config integrity verification and automatic repair.
- Built-in version detection and update mechanism.

---

© 2025 VergeGrid Installer Project — *Sonja + GPT Collaboration*
