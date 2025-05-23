from loguru import logger
from pydantic import BaseModel


class Params(BaseModel):
    class Dependencies(BaseModel):
        bfabric_scripts: str = "bfabric-scripts==1.13.28"
        bfabric_app_runner: str = "bfabric-app-runner==0.0.22"

    dependencies: Dependencies
    working_directory: str
    workunit_id: int
    app_yaml_path: str


def main() -> None:
    """Dummy main function."""
    logger.success("Dummy wrapper does not do anything.")


if __name__ == "__main__":
    main()
