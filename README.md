# postgres-genealogy-project
group project on db design + ETL pipeline w/ postgresql

To install dependencies + set up environment:
```bash
uv sync
```

To run main():
```bash
uv run main.py
```

To install LaTeX: (VERY HEAVY, AROUND 2-3 GB CAREFUL)
```bash
sudo apt install texlive-latex-recommended
sudo apt install texlive-publishers
sudo apt install texlive-science
sudo apt install texlive-lang-cjk
sudo apt install chktex
```

To compile LaTeX:
```bash
#Inside ./report
pdflatex main.tex
```