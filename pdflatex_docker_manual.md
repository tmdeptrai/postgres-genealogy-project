# Building and Compiling the LaTeX Report with Docker

First, build the image:
```bash
docker build -t genealogy-report .
```

Then, compile the report:
```bash
docker run --rm -v $(pwd)/report:/workspace genealogy-report
```

You can run the second command as many times as you want without rebuilding the image.

## Output

After successful compilation, you'll find:
- `main.pdf` - The compiled PDF report
- `main.aux`, `main.log` - Auxiliary files (can be deleted)

## Troubleshooting

**Error: "Docker daemon is not running"**
- Make sure Docker Desktop is open and running

**Error: "Cannot find main.tex"**
- Make sure you're running the command from the project root directory (where the `Dockerfile` is)
- Make sure the `report/main.tex` file exists

**Missing figures in PDF**
- Make sure the `figures/` directory is in the project root and contains the images referenced in `main.tex`

## Manual Commands (if needed)

If you want to use the Docker image directly without the Dockerfile:

```bash
docker run --rm -it \
  -v $(pwd)/report:/workspace \
  -w /workspace \
  sauerburger/pdflatex:latest \
  pdflatex -interaction=nonstopmode main.tex
```

This mounts your local `report/` directory to `/workspace` in the container and compiles `main.tex`.
