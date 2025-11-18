==================================================

PROJECT_STRUCTURE.md

VergeGrid Project Structure

This file defines the recommended directory layout for all VergeGrid components.

==================================================

Root Layout
VergeGrid/
   installer/
   modules/
   physics/
   viewer/
   webui/
   docs/


==================================================

Installer
installer/
   vergegrid-install.ps1
   templates/
   logs/
   config/


Handles full automated deployment.

==================================================

Modules
modules/
   HybridEEP/
   InShape/
   CrossRegion/
   Money-GloBits/
   AdminTools/


Each module self-contained with config + README.

==================================================

Physics
physics/
   physx-wrapper/         (your fork of MOSES wrapper)
   VergeGrid-PhysX/       (C# plugin for OpenSim)
      src/
      module.ini
      vergegrid-physx.csproj
   docs/


==================================================

Viewer
viewer/
   firestorm/
      patches/
      build/
      README.md


==================================================

Web UI
webui/
   admin/
      api/
      templates/
      auth/
   user/


==================================================

Docs
docs/
   ROADMAP.md
   MILESTONES.md
   CONTRIBUTING.md
   PROJECT_STRUCTURE.md
   ARCHITECTURE.md


==================================================