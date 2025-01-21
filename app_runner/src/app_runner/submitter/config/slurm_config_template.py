from app_runner.specs.config_interpolation import VariablesApp, interpolate_config_strings, VariablesWorkunit
from app_runner.submitter.config.slurm_config import _SlurmConfigBase, SlurmConfig


class SlurmConfigTemplate(_SlurmConfigBase):
    def evaluate(self, app: VariablesApp, workunit: VariablesWorkunit) -> SlurmConfig:
        data_template = self.model_dump(mode="json")
        data = interpolate_config_strings(data=data_template, variables={"app": app, "workunit": workunit})
        return SlurmConfig.model_validate(data)
