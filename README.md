# Learn & Fix: Interactive Topology Feedback System

Learn & Fix is an educational Blender add-on developed to assist novice 3D modellers in identifying, navigating, and understanding topological errors. Designed from a Human-Computer Interaction (HCI) perspective, it functions as an "active instructional scaffold." It utilises the BMesh API and an event-driven architecture to detect geometric irregularities in real time, providing context-sensitive pedagogy while explicitly avoiding automated "auto-fixing" to encourage skill acquisition.

This software was developed as part of the article: Bridging the Learning Gap in 3D Modelling: Design of an Interactive Topology Feedback System for Blender.

## Overview

Unlike standard mesh checkers that act as post-process 'spellcheckers', this add-on implements a real-time, event-driven observer architecture. It continuously monitors modelling operations to provide immediate feedback without degrading viewport performance. Through its "Explain & Fix" pedagogical dialogue, it guides users to manually resolve issues, turning debugging into a formative learning opportunity.

### Core Functionalities
1. **Event-Driven Detection:** Real-time background scanning for fundamental geometric and topological errors.
2. **Pedagogical Scaffolding:** An integrated "Explain & Fix" system that provides clear diagrams and theoretical explanations for each error type.
3. **Interactive Navigation:** Smoothly isolates the affected geometry using spherical linear interpolation (slerp) for the 3D viewport camera.
4. **Visual Distinction UI:** Features a dynamic floating Heads-Up Display (HUD) and visual alert indicators designed specifically for discoverability by novice users.

## Supported Error Checks

As an entry-level instructional tool, the detection system focuses on a foundational pedagogical progression (from object-level data to topology optimisation) consisting of four core checks:

* **Unapplied Transforms:** Detects unapplied scale and rotation discrepancies at the object level.
* **Zero-Area Faces:** Identifies degenerate triangles/polygons mathematically acting as computational noise (Area < 1e-8).
* **Self-Intersections:** Utilises Bounding Volume Hierarchy (BVH) trees to detect overlapping spatial volumes and intersecting geometric planes.
* **N-gons:** Flags polygons with >4 vertices as a strict entry-level training constraint for topology optimisation.

## Technical Architecture
* **Compatibility:** Tested on **Blender 3.6 LTS** and **4.0**.
* **Language:** Python 3.10+
* **API:** Blender Python API (`bpy`, `bmesh`, `mathutils.bvhtree`).
* **Structure:** Modular design mapping specific algorithms to isolated detection workflows.
* **Event System:** Uses `bpy.app.handlers` (`on_depsgraph_update`) to monitor dependency graph updates, filtering events to trigger analysis only after significant mesh alterations.

## Installation

1. Download the latest release (`.zip`).
2. Open Blender (Version 3.6 LTS or 4.0).
3. Navigate to **Edit > Preferences > Add-ons**.
4. Click **Install...** and select the downloaded .zip file.
5. Enable the checkbox next to **"3D View: Learn & Fix"**.
6. A visual indicator will flash to help you locate the tool. You can access the primary interface via the custom floating HUD and the Sidebar (N-Panel).

## Usage Guide

### 1. Configuration
Select a **Workflow Mode** (e.g., 3D Printing, Game Assets). This automatically filters relevant error checks to avoid overwhelming the user (a focused-attention strategy).

### 2. Analysis
The event-driven observer will monitor your mesh. You can also manually click **Check Mesh** to run the detection algorithms. The add-on will display a categorised list of found errors.

### 3. Navigation & Correction
* **Next/Prev:** Cycles through the list of errors.
* **Focus (Camera Icon):** Uses cinematic camera navigation (slerp) to isolate the exact problematic faces/vertices.
* **Explain & Fix (?):** Opens the pedagogical dialog explaining *why* this geometry is flawed and *how* to manually correct it. 

## Project Structure

* `__init__.py`: Registry, event handlers, and core operator logic.
* `checks/`: Directory containing individual detection modules and BVH algorithms.
* `docs/`: Rich Text Format files used for the internal documentation system.
* `icons/`: UI assets.

## License

This project is open-source and available under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for more information.
