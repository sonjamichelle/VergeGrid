==================================================

ARCHITECTURE.md

VergeGrid Architecture

VergeGrid is a modular, extensible, OpenSimulator-based virtual world platform. Its architecture avoids core forks and favors standalone modules, plugins, and external services. This ensures long-term compatibility with upstream OpenSim, easier updates, and clean separation of concerns.

This document describes the full architectural design of VergeGrid.

==================================================

1. Philosophy

No OpenSim forks. Only one optional patch (draw distance).

Modular everything. Physics, environment, movement, crossings, currency.

External services preferred. Phone app integration, admin UI, metrics.

Viewer-independent. Viewer modifications optional, not required.

Future-safe. All modules are replaceable or upgradable without rewriting.

==================================================

2. High-Level Overview
+--------------------------------------------------------------+
|                           VergeGrid                          |
|                                                              |
|  +-------------------+   +------------------+                |
|  | OpenSim Standard  |   | Robust Services  |                |
|  |    (Upstream)     |   | (Unmodified)     |                |
|  +-------------------+   +------------------+                |
|             |                        |                       |
|   +---------------------+   +-----------------------+        |
|   | VergeGrid Modules   |   | VergeGrid External    |        |
|   | (C# region/shared)  |   | Services (web/apps)   |        |
|   +---------------------+   +-----------------------+        |
|                                                              |
|         Viewer (Firestorm / VG Viewer)                       |
+--------------------------------------------------------------+


==================================================

3. Core System Layers

VergeGrid is composed of the following architectural layers:

3.1 OpenSim Layer (Upstream)

Stock OpenSim simulator

Stock Robust services

Unmodified core code

Only exception: optional draw distance patch

3.2 VergeGrid Module Layer

All custom logic lives here:

PhysX Physics plugin

Hybrid WindLight/EEP module

InShape movement module

Region crossing enhancements

GloBits currency module

Admin Tools

Environmental controllers

Path/waypoint management

Modules are:

Self-contained

Configurable

Loaded dynamically

Version-independent whenever possible

3.3 External Services Layer

These include:

Web UI (admin and user)

REST API for InShape

Data synchronization services

Optional wearable integration APKs

Logging and monitoring endpoints

Runs independently of OpenSim.

3.4 Viewer Layer

Optional:

VergeGrid Viewer (Firestorm fork)

Removed draw distance cap

Optional UI tweaks

Viewer enhancements are isolated so standard viewers still work.

==================================================

4. Physics Architecture (PhysX Integration)

PhysX integration uses two distinct components:

4.1 Native Layer (C++)

Located in physx-wrapper:

Wraps the NVIDIA PhysX SDK

Exposes simple C API functions

Handles memory management

Implements rigid bodies, materials, and collisions

Exports clean functions callable via C#

4.2 Managed Layer (C# Module)

Located in VergeGrid-PhysX:

Implements OpenSim’s IPhysicsPlugin and IPhysicsScene

Loads the native wrapper via P/Invoke

Handles avatar movement

Handles scene stepping

Provides region-based physics scenes

Injected via OpenSim.ini

This forms:

OpenSim → VergeGrid-PhysX.dll → physx-wrapper.dll → PhysX SDK


==================================================

5. InShape Architecture

The InShape revival consists of:

A. Region Module

Binds avatars to InShape paths

Handles movement updates

Integrates with avatar physics

Coordinates region crossings

B. Path / Waypoint Engine

Stored per-region or in DB. Handles:

Trail definitions

Smooth turns

Speed interpolation

Repeat loops

C. External Phone App

Sends accelerometer data

Optionally sends biometric data

Communicates via HTTPS REST API

D. Movement Controller

Avatar moves based on real-world motion

Predictive interpolation

Smooth transfer across adjacent regions

==================================================

6. Environment Architecture (WindLight/EEP Hybrid)

This module:

Reads WindLight-style commands from region description

Parses settings into modern EEP-compatible structures

Dynamically generates EEP assets

Sends EEP to viewer

Maintains simple user workflow

No reliance on deprecated WindLight code.

==================================================

7. Region Crossing Architecture

Enhancements implemented via modules:

Predictive border timing

Velocity preservation

Better agent update ordering

Sync smoothing between neighbors

Improved movement under PhysX

No invasive simulator rewrites.

==================================================

8. Web UI Architecture

The Admin Web UI uses:

Apache/PHP or Python backend

Direct MySQL queries

Optional REST endpoints

Role-based access control

Region start/stop tools

Logs and monitoring

Runs independently of simulator processes.

==================================================

9. Installer Architecture

PowerShell and Python-based system that:

Installs all dependencies

Generates OpenSim.ini and Robust.ini

Auto-creates region files, estates, god avatar

Configures SSL certificates

Logs all operations

Ensures consistent environment

==================================================

10. Viewer Architecture

Viewer modifications (optional):

Remove draw distance clamp

Branding and theme updates

Quality-of-life UI improvements

Standard viewers remain compatible.

==================================================