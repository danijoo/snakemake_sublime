# Snakemake Sublime

Build System, Syntax Highlighting and Snippets for Snakemake


### Building
The build system will automatically pick up the Snakefile if one is opened
or in the current folder. Paths can also be specified in the sublime project
file:

```json
{
    "folders":
    [
        {
            "path": "."
        }
    ],
    "snakemake": {
        "snakefile": "./Snakefile",
        "working_dir": "/home/some_user/projects/snakemake_example_project"
    }
}
```
