==================================================

CONTRIBUTING.md

Contributing to VergeGrid

VergeGrid is a modular ecosystem that allows contributions in multiple areas such as physics, web tools, installers, viewers, and environment systems. All contributions must respect VergeGrid’s core philosophy:

No OpenSim forks. No invasive rewrites. Everything must be modular and maintainable.

==================================================

How to Contribute
1. Modules and Addons

All new functionality must be implemented as:

Region modules

Shared modules

Standalone services

External tools

Viewer patches

Never modify OpenSim source unless absolutely necessary.

2. Code Style

Use clear, readable code

Comment interfaces and exported functions

Keep P/Invoke signatures clean and consistent

Prefer composition over inheritance

No magic values hardcoded; use config files

3. Documentation

Every module must include:

README

Example config

Behavior summary

Dependencies list

4. Testing

Contributors must test:

Single-region behavior

Multi-region behavior

Region crossings

Avatar collisions

Basic performance under load

5. Pull Requests

All PRs must:

Explain what problem the change solves

Include minimal test notes

Avoid touching OpenSim core unless approved

==================================================

Reporting Issues

Please include:

Logs

Environment

Reproduction steps

Region count

Binary versions

Config snippets

==================================================

Thank You

Every improvement pushes VergeGrid closer to its goals.
We appreciate any help that follows the project’s clean, modular design.