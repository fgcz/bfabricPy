import cyclopts

from bfabric_scripts.cli.dataset.download import cmd_dataset_download
from bfabric_scripts.cli.dataset.upload import cmd_dataset_upload
from bfabric_scripts.cli.dataset.show import cmd_dataset_show

app = cyclopts.App()
app.command(cmd_dataset_upload, name="upload")
app.command(cmd_dataset_download, name="download")
app.command(cmd_dataset_show, name="show")
