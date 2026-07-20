# Eikanya | Live2D Character Archive 🐙

A high-fidelity, high-resolution archive of **Eikanya's** Live2D models, featuring both modern `.moc3` (Cubism 3/4) and legacy `.moc` (Cubism 2.x) runtimes. All preview thumbnails are rendered at 5000px native canvas resolution with perfect model centering and automatic alpha-transparency border trimming.

## 🔗 Live Gallery
**[View the Archive on GitHub Pages](https://dasilva333.github.io/live2d-eikanya-index/)**

## 📂 Project Overview
This project uses a highly resilient, headless rendering pipeline to batch-process 4,924 Live2D assets into clean, transparent PNGs, exposing them via an interactive, serverless catalog interface.

### Tech Stack
* **Engine**: PIXI 7 with `pixi-live2d-display` (Cubism 2.x & Cubism 3/4 SDK core runtimes loaded side-by-side)
* **Environment**: Puppeteer (Headless Chrome browser worker queue with WebGL page-level crash recovery)
* **Processing**: Sharp (Automatic trimming of empty border bounds, resized down to 1024x1024 containment)
* **Frontend**: Glassmorphic dashboard hub, paginated franchise cards, local metadata search index, and client-side ZIP on-demand packaging.

## 📜 Data Source
The raw Live2D assets were sourced from the community preservation repository **[Eikanya/Live2d-model](https://github.com/Eikanya/Live2d-model)**. All assets belong to their respective original copyright holders and developers.

## 🛠️ How it Works
1. **Fuzzy Express Server**: Hosts the Live2D folders locally during thumbnail rendering, employing custom static middleware to fuzzy-search folder-case mismatches, missing file extensions, and resolve URL hash fragment characters (`#` to `%23`).
2. **Headless Puppeteer Worker Queue**: Sequentially loads models inside a 5000x5000 viewport, auto-monitoring canvas bindings and WebGL fatigue.
3. **Pixi Texture Garbage Collection**: Purges GPU cache bindings (`texture: true, baseTexture: true`) during model swaps to prevent WebGL driver crashes.
4. **Sharp Trimming**: Trims alpha-channels to crop the raw screenshot to the model's exact outer margins, saving the layout to flat files.
5. **Decoupled Zip Downloader**: The static gallery portal stores no raw files locally. Clicking "Download Package" streams raw files directly from Eikanya's master repository branch into the user's browser via `JSZip`, formats the `.model3.json` texture layering (sorting blooms to render correctly), and serves the compiled ZIP file.

---
*Generated with 🐙 Antigravity*
