import cyclopts

from bfabric_scripts.cli.dataset.download import cmd_dataset_download
from bfabric_scripts.cli.dataset.upload import cmd_dataset_upload
from bfabric_scripts.cli.dataset.show import cmd_dataset_show

cmd_dataset = cyclopts.App(help="Read and update dataset entities in B-Fabric.")
_ = cmd_dataset.command(cmd_dataset_upload, name="upload")
_ = cmd_dataset.command(cmd_dataset_download, name="download")
_ = cmd_dataset.command(cmd_dataset_show, name="show")
