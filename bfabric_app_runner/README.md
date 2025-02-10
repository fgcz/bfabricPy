The app runner is an experimental tool that standardizes the integration of one-off apps into B-Fabric.

**The API is subject to drastic changes in the next time.**

The main idea is that an app provides a specification of the following steps:

- dispatch -> create `inputs.yml` files and 1 `chunks.yml` file
- process -> process a particular chunk (after inputs have been prepared)
- collect -> collect the results of a chunk and create `outputs.yml` files

The individual app can be in a container environment or a script running in the same environment as the app runner.

To make this possible input and output staging is abstracted and communicated through `inputs.yml` and `outputs.yml`
specification files.
A command is available to stage the inputs or register the outputs respectively then.
