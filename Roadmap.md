==================================================

ROADMAP.md
VergeGrid Project Roadmap
Overview

VergeGrid is a next-generation OpenSimulator-based virtual world platform designed to bring forward the best features from SL, Halcyon, nWorlds, and MOSES, using modules and external services, not forks.

Core philosophy:

No forking OpenSim.

No deep core rewrites.

Everything must be modular, maintainable, and future-safe.

Only one tiny upstream patch (draw distance).

Everything else loads through plugins, modules, and tools.

This roadmap outlines the core components that define VergeGrid.

==================================================

1. Installer + Bootstrap System

A full installer and provisioning system that:

Installs MySQL, OpenSim, Apache, PHP, LetsEncrypt

Creates all required directories

Configures MySQL schemas and launches Robust to populate them

Applies OpenSim.ini and Robust.ini templates

Provides fully verbose logging and no silent installs

Requires no manual prompts or interactive setup

Purpose: Fully automated, predictable, repeatable grid deployment.

==================================================

2. Automatic Region, Estate, and God Avatar Creation

Before OpenSim.exe is launched:

Auto-generate region files

Create estate records

Create a god-level admin/avatar

Ensure the simulator boots unattended on first run

This guarantees that OpenSim never pauses waiting for estate or region input.

==================================================

3. Admin Web UI

A PHP/Python-based web dashboard for:

Region management

User management

Grid tools

Server status and statistics

Eventually: user portal features

This UI is external and never modifies OpenSim core.

==================================================

4. GloBits Currency Integration

Install and configure the GloBits money module

Configure endpoints and wallet settings

Enable it within Robust and OpenSim modules

Documentation for grid owners on configuration

This allows integrated currency support without modifying core code.

==================================================

5. Draw Distance Patched OpenSim Build

The only upstream patch VergeGrid will maintain:

Pull OpenSim source

Apply minimal draw distance patch

Rebuild using MSBuild

Maintain a small, clean patchset for version updates

Everything else remains stock OpenSim.

==================================================

6. Custom Viewer Build (VergeGrid Viewer)

Pull Firestorm (or chosen viewer) source

Remove viewer-side draw distance limitations

Apply any small viewer UX fixes

Compile and brand as “VergeGrid Viewer”

Optional: packaged distribution for users

Viewer modifications remain separate from server logic.

==================================================

7. Region Crossing Improvements

Inspired by Halcyon and nWorlds:

Improve avatar border prediction

Improve timing of handoffs

Reduce teleport-style snaps

Increase consistency and reduce desync

Implement through modules and extension hooks

Only minimal core hooks used if unavoidable. No refactoring or forking.

==================================================

8. PhysX Physics Engine Plugin

Using the forked MOSES physx-wrapper (https://github.com/sonjamichelle/physx-wrapper
):

Build PhysX native DLL with CPU-mode SDK

Build C# plugin implementing OpenSim’s physics interfaces

Drop-in physics engine selectable via OpenSim.ini

Supports rigid bodies, characters, collision stability

No GPU dependency, no Nvidia licensing issues

This becomes VergeGrid’s advanced physics alternative to BulletSim.

==================================================

9. Hybrid WindLight/EEP Environment System

A compatibility layer allowing simple WindLight commands with full EEP output:

Region owners enter classic WindLight syntax

Module parses commands and generates EEP assets on the fly

Viewer receives proper EEP

Users retain WindLight simplicity

This protects creators from EEP complexity while remaining future-proof.

==================================================

10. Full InShape Revival

A complete recreation and enhancement of the nWorlds InShape system:

Core capabilities:

In-world InShape markers (stations)

Avatar attaches to a path or waypoint system

Server controls avatar motion through regions

Android phone app sends accelerometer data

Avatar walks/runs based on real-world movement

Region crossing support with motion persistence

Optional expansions:

Fitness wearable integration (Fitbit, Galaxy Watch, Apple Watch)

Heart rate, step count, speed, and other stats

In-world HUD displays biometrics

Custom InShape-based trails and routes

The entire system runs through modules + external services.

==================================================

Summary

VergeGrid’s roadmap focuses on:

Modular feature development

No OpenSim fork

Long-term maintainability

Physics and movement innovation

Realistic, user-friendly environment controls

Automatic deployment and easy administration

Optional viewer enhancements

This roadmap ensures VergeGrid delivers a modern, stable, and feature-rich virtual world without sacrificing compatibility with upstream OpenSimulator.

==================================================