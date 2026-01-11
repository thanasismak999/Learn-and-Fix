# Learn & Fix: Automated Mesh Analysis Tool

**Learn & Fix** is a Blender add-on developed to assist 3D modelers in identifying, navigating, and understanding topological errors. It functions as both a diagnostic tool and an educational resource, utilizing the BMesh API to detect geometric irregularities while providing context-sensitive documentation on how to resolve them.

This software was developed as part of the thesis: *[Insert Your Thesis Title Here]*.

## Overview

Unlike standard mesh checkers that provide only a list of indices, this tool implements a "smart assistant" workflow. It continuously monitors modeling operations to provide real-time feedback and includes a "Learn" module that explains the theoretical background of detected errors (e.g., why N-Gons affect subdivision surfaces).

### Core Functionalities
1.  **Automated Detection:** Scans for 15 distinct topological and geometric error types.
2.  **Interactive Navigation:** Smoothly interpolates the 3D viewport camera to specific error locations (Vertices/Faces).
3.  **Contextual Education:** Integrated "Explain & Fix" system providing diagrams and text explanations for every error type.
4.  **Workflow Presets:** Pre-configured detection profiles for different industries (3D Printing, Game Dev, Animation).

## Features

### Supported Error Checks
The detection system covers four primary categories:

* **Topology:** N-Gons (>4 verts), Poles (N/E-Poles with curvature filtering), Thin/Degenerate Triangles, Edge Flow disruptions.
* **Geometry:** Non-Manifold edges, Open Holes, Internal Faces, Self-Intersections, Isolated Vertices, Duplicate Vertices.
* **Surface:** Flipped Normals, Inconsistent Normals, Overlapping UVs.
* **Object Data:** Unapplied Transforms (Scale/Rotation), Origin Offsets.

### Technical Architecture
* **Language:** Python 3.10+
* **API:** Blender Python API (`bpy`, `bmesh`)
* **Structure:** Modular design with separated logic (detection scripts) and presentation (UI/operators).
* **Event System:** Uses `bpy.app.handlers` to monitor dependency graph updates, triggering analysis only after significant geometry changes.

## Installation

1.  Download the latest release (`.zip`).
2.  Open Blender (Version 3.0 or newer).
3.  Navigate to **Edit > Preferences > Add-ons**.
4.  Click **Install...** and select the downloaded zip file.
5.  Enable the checkbox next to **"3D View: Learn & Fix"**.
6.  The interface will appear in the Sidebar (N-Panel) under the "Learn&Fix" tab.

## Usage Guide

### 1. Configuration
Select a **Workflow Mode** from the main panel (e.g., "3D Printing"). This automatically enables the relevant error checks and disables irrelevant ones (e.g., ignoring Edge Flow for print-ready models).

### 2. Analysis
Click **Check Mesh** to run the detection algorithms. The add-on will display a health percentage and a categorized list of found errors.

### 3. Navigation
* **Next/Prev:** Cycles through the list of errors.
* **Show:** Snaps the view to the current error.
* **Explain (?):** Opens the documentation popup for the current error type.

## Project Structure

* `__init__.py`: Registry and core operator logic.
* `checks/`: Directory containing individual detection modules (e.g., `check_ngons.py`).
* `docs/`: Rich Text Format files used for the internal documentation system.
* `icons/`: UI assets.

## License

This project is open-source and available under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for more information.
