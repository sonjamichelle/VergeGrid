==================================================

		CROSS_PLATFORM.md

==================================================

Cross-Platform Requirements

Core Principles - Windows + *nix Support (*nix eg:Linux, BSD, Unix)

VergeGrid’s architecture needs to remain fully operational on both Windows and *nix. That means every module, plugin, wrapper, and tool must follow cross-platform rules, including:

No OS-specific physics dependencies

No Windows-only DLL hell

No *nix-only hacks

No hard paths

No platform-locked viewer dependency

Below is your exact cross-platform technical requirement list.

==================================================

1. OpenSim Core Compatibility

(OpenSim officially supports Windows & *nix)

Nothing special required, but you must:

✔ Build your modules for .NET Framework / Mono compatible targets
✔ Avoid any Windows-exclusive APIs in C#
✔ Avoid P/Invoke calls into OS libraries
✔ Use managed-only logic whenever possible
✔ Keep all paths relative

==================================================

2. PhysX Wrapper Cross-Platform Requirements

This is the big one.

PhysX itself supports:

Windows (native)

*nix (native)

MOSES’s wrapper can be made cross-platform, but you must follow these hard rules:

✔ 1. Build two native wrapper binaries:
physx-wrapper.dll        (Windows)
physx-wrapper.so         (*nix)

✔ 2. Wrap ONLY the PhysX SDK — no OS APIs

Do not call any Windows APIs or POSIX APIs directly.

✔ 3. No C++/CLI

C++/CLI is Windows-only
Your MOSES wrapper is pure native C++ = Good

✔ 4. P/Invoke must use platform conditions

In your C# plugin:

#if WINDOWS
    const string PhysXLib = "physx-wrapper.dll";
#else
    const string PhysXLib = "physx-wrapper.so";
#endif

✔ 5. Bundle BOTH versions

Folder should look like:

/bin/PhysX/
    windows/
        physx-wrapper.dll
        PhysX_64.dll
        etc...
    *nix/
        libphysx-wrapper.so
        libPhysX.so
        etc...


OpenSim loads the correct one based on OS.

==================================================

3. Hybrid Environment System (WindLight/EEP)

Entirely C#.
No OS dependencies.

Just ensure:

✔ use UTF-8 file IO
✔ no backslashes in paths
✔ avoid Windows-only path normalization

100 percent cross-platform out of the box.

==================================================

4. InShape External Services

Your REST API server + phone app must:

✔ Listen on all interfaces (0.0.0.0)
✔ Use OS-neutral HTTP libraries
✔ Avoid file watching APIs (these differ between OSes)
✔ Use Python/Flask, NodeJS, or .NET Core — all cross-platform

If you bake it into OpenSim as a module:

✔ Do NOT use HttpListener (Windows-only on old Mono)
✔ Use OpenSim’s built-in IHttpServer interfaces (already cross-platform)

==================================================

5. Admin Web UI (Apache/PHP or Python)

*nix and Windows both support:

Apache

PHP

Python Flask

NodeJS

MariaDB/MySQL connectors

For full cross-platform:

✔ Use PHP 7+/8+ or Python 3
✔ Avoid Windows-specific paths
✔ Always use lowercase filenames (*nix is case-sensitive)

==================================================

6. Installer System

(Windows installer vs *nix installer)

Windows installer:

PowerShell 5/7

Python

Batch fallback

Build everything using Visual Studio Build Tools

*nix installer:

Bash

Python

Standard *nix build tools

MySQL/MariaDB packages

To unify installers:

✔ Put all logic into Python whenever possible
✔ Use PowerShell only for Windows-specific tasks
✔ Avoid binary tools that only exist on one OS

==================================================

7. OpenSim Module Development Requirements

All your modules must:

✔ Target .NET Framework 4.6.1 for Windows
✔ Target Mono-compatible IL for *nix
✔ Avoid System.Drawing (not supported on *nix)
✔ Avoid Windows registry
✔ Avoid COM interop
✔ Avoid P/Invoke unless you wrap your own cross-platform libraries
✔ Use Path.Combine() not string paths
✔ Use OpenSim's plugin loading system (works the same on both OSes)

==================================================

8. Viewer (Firestorm / VergeGrid Viewer)

Viewer builds differ per OS.

You need:

✔ Separate build pipelines:

Windows viewer: Visual Studio

*nix viewer: GCC/Clang, QMake

✔ Shared patches:

Draw distance removal

Viewer UI elements

Viewer binaries cannot be cross-compiled.
But the source patches MUST be cross-platform.

==================================================

9. Logging and Paths
Required:

✔ Use forward-slashes internally (/)
✔ Use Path.Combine in C#
✔ No absolute paths
✔ Use environment variables for data directories

%APPDATA%/VergeGrid (Windows)

$HOME/.vergegrid (*nix)

==================================================

10. Database Layer (MySQL/MariaDB)

Identical behavior on both OSes.

Ensure:

✔ Connection strings do not contain Windows-only paths
✔ Dump/restore scripts are POSIX-compatible
✔ UTF-8 encoding everywhere

==================================================

11. Packaging and Deployment

You will ship:

VergeGrid/
   windows/
       installer.ps1
       OpenSim-windows/
       PhysX/windows/
       viewer/windows/

   *nix/
       installer.sh
       OpenSim-*nix/
       PhysX/*nix/
       viewer/*nix/


Everything modular.
Everything OS-agnostic.

==================================================

SUMMARY: Required Cross-OS Capabilities

Here’s the final list as a clean bullet-point drop-in:

Core Cross-Platform Requirements

All modules written in pure C# (Mono compatible)

PhysX wrapper compiled separately for Windows and *nix

P/Invoke conditionally loads DLL vs SO

Environment system OS-neutral

InShape API uses cross-platform HTTP

Admin Web UI uses PHP or Python (both cross-platform)

Installer logic favors Python

Viewer source patches cross-platform

Paths normalized with Path.Combine

No OS-specific APIs allowed

PhysX-Specific

physx-wrapper.dll for Windows

libphysx-wrapper.so for *nix

P/Invoke selection logic

No C++/CLI

Pure native C++ with PhysX SDK links

InShape-Specific

Use OpenSim’s HTTP server, not OS-native listeners

Android/IOS app connects via REST (OS-neutral)

==================================================