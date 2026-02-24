# Use the pdflatex Docker image as base
FROM sauerburger/pdflatex:latest

# Set working directory in the container
WORKDIR /workspace

# Copy the entire report directory into the container
COPY report/ /workspace/

# Copy the figures directory if it exists
COPY figures/ /figures/

# Set the default command to compile the LaTeX file
CMD ["pdflatex", "main.tex"]
