# VolSU NIR LaTeX Project (local VS Code workflow)

This repository uses your original Overleaf template and build method:

- entry file: `Thesis.tex`
- class/style: `disser` + `VolSU.rtx`
- bibliography: `biblatex-gost` + `biber`
- editor: VS Code + `LaTeX Workshop`

## Prerequisites (Windows)

1. Install MiKTeX:
   - `winget install --id MiKTeX.MiKTeX -e --accept-source-agreements --accept-package-agreements`
2. Restart VS Code and terminal.
3. Open `MiKTeX Console` and set:
   - `Settings -> General -> Install missing packages -> Always`

## VS Code setup

- Required extension: `james-yu.latex-workshop` (recommended in `.vscode/extensions.json`).
- Workspace settings are in `.vscode/settings.json`.
- Default recipe:
  - `pdflatex -> biber -> pdflatex * 2`
- Fallback recipe:
  - `latexmk (pdfLaTeX)`

## Build

- Manual build in VS Code:
  - Command Palette -> `LaTeX Workshop: Build LaTeX project`
- Auto build:
  - runs on every save of `.tex` files (`latex-workshop.latex.autoBuild.run = onSave`)

Terminal fallback build (from repo root):

```powershell
pdflatex Thesis.tex
biber Thesis
pdflatex Thesis.tex
pdflatex Thesis.tex
```

## Where to edit content

- Title page metadata: `Title.tex`
- Main document pipeline: `Thesis.tex`
- Chapters and sections: `Intro.tex`, `Chapter1.tex`, `Chapter2.tex`, `Chapter3.tex`, `Conclusion.tex`, `Progress.tex`, `Appendix.tex`
- Bibliography database: `Bib.bib`
- Figures: `fig/`

## Git policy

- Build artifacts and generated PDFs are ignored via `.gitignore`.
- Keep only source files under version control.
