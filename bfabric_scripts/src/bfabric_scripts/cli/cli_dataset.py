import cyclopts

from bfabric_scripts.cli.dataset.download_dataset import download_dataset
from bfabric_scripts.cli.dataset.upload_dataset import upload_dataset

app = cyclopts.App()
app.command(upload_dataset, name="upload")
app.command(download_dataset, name="download")
