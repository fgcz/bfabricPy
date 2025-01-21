from app_runner.submitter.config.slurm_config import _SlurmConfigBase, SlurmConfig


class SlurmConfigTemplate(_SlurmConfigBase):
    def evaluate(self) -> SlurmConfig:
        raise NotImplementedError
