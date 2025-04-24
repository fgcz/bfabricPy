This is a very simple demo app.
It will perform the following operation:

- Given input files, it will calculate the checksum of each file.
- These checksums will be printed to markdown and included in a zip file.
- The zip file will be uploaded to B-Fabric.

## Stack

- This application uses Snakemake.
- Input files will be linked instead of copied.
- A snakemake rule computes the checksum of each input file.
- The results will be collected by a Python script which generates the markdown report.
- This file will be zipped and staged to B-Fabric.

## Input

This is a dataset flow application, requiring the input table to provide a "Resource" and "Relative Path" column to identify the
resources in B-Fabric. (resource, and relative_path, are how these will be treated internally and you could also try
to name them like this in your input dataset)
