README.md

VergeGrid

VergeGrid is a next-generation OpenSimulator-based virtual world platform built entirely through modules, plugins, and external services, without forking OpenSim. The goal is simple: deliver the best features from SL, Halcyon, nWorlds, MOSES, and Aurora in a modern, stable, future-proof grid architecture.

VergeGrid is designed and built by Sonja and Nikki as an advanced, modular replacement for existing OpenSim distributions with a strong focus on:

Real physics

Smooth region crossings

Environment realism

Automated deployment

Phone-driven avatar movement

Modern viewer experience

Zero-maintenance upgrades

VergeGrid stays fully compatible with upstream OpenSim except for one tiny, deliberate patch (draw distance limit removal).

==================================================

Core Features

Installer & Bootstrap
Automated setup of MySQL, OpenSim, Apache, PHP, LetsEncrypt, region files, estates, and admin avatars.

Admin Web UI
Grid management, user tools, stats, and region oversight.

GloBits Integration
Currency support using the existing module system.

Patched OpenSim
Only modification: removing the draw distance clamp. Everything else remains stock.

Custom VergeGrid Viewer
A viewer with removed draw distance limit and optional interface enhancements.

Region Crossing Enhancements
Halcyon/nWorlds-inspired border smoothing implemented through modules.

PhysX Module
A fully modular PhysX physics engine using the MOSES physx-wrapper for rigid bodies and avatar stability.

Hybrid WindLight/EEP
WindLight-style commands, EEP-style results, simple for creators and future-proof.

InShape Revival
Phone-driven avatar movement, real-world walking and running, waypoint paths, wearable integrations, and HUD feedback.

==================================================

Philosophy

Never fork OpenSim.

Never fight upstream.

Always use modules.

Minimal patches, maximum compatibility.

Everything is replaceable, injectable, and future-resistant.

==================================================

Status

Under rapid development.
See MILESTONES.md for progress tracking.

==================================================

License

GNU General Public License v3.0
GNU GPLv3

Permissions of this strong copyleft license are conditioned on making available complete source code of licensed works and modifications, which include larger works using a licensed work, under the same license. Copyright and license notices must be preserved. Contributors provide an express grant of patent rights.

Permissions	Conditions	Limitations
 Y - Commercial use
 Y - Distribution
 Y - Modification
 Y - Patent use
 Y - Private use
 Y - Disclose source
 Y - License and copyright notice
 Y - Same license
 Y - State changes
 N - Liability
 N - Warranty
==================================================