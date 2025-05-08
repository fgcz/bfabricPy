from pathlib import Path
from unittest.mock import MagicMock

from bfabric_app_runner.actions.config_file import ActionConfig, FromConfigFile


class TestActionConfig:
    def test_ensure_app_ref_path_existing_path(self, mocker):
        """Test ensure_app_ref_path_if_path when path exists"""
        # Mock Path.exists to return True
        mocker.patch.object(Path, "exists", return_value=True)

        # Test with a string that should be converted to Path
        test_path = "/path/to/app"
        result = ActionConfig.ensure_app_ref_path_if_path(test_path)

        # Verify result is a Path object
        assert isinstance(result, Path)
        assert str(result) == test_path

    def test_ensure_app_ref_path_non_existing_path(self, mocker):
        """Test ensure_app_ref_path_if_path when path doesn't exist"""
        # Mock Path.exists to return False
        mocker.patch.object(Path, "exists", return_value=False)

        # Test with a string that should remain a string
        test_path = "/path/to/nonexistent/app"
        result = ActionConfig.ensure_app_ref_path_if_path(test_path)

        # Verify result remains a string
        assert isinstance(result, str)
        assert result == test_path


class TestFromConfigFile:
    def test_parse_config_file(self, mocker):
        """Test parse_config_file method with valid config"""
        # Sample YAML content for mocking
        yaml_content = """
        bfabric_app_runner:
          action:
            work_dir: /test/work/dir
            app_ref: /test/app/ref
            ssh_user: testuser
        """

        # Create a mock for open function
        mock_file = mocker.mock_open(read_data=yaml_content)

        # Mock Path.open to return our mock file
        mocker.patch("pathlib.Path.open", mock_file)

        # Mock yaml.safe_load to return expected structure
        expected_yaml_data = {
            "bfabric_app_runner": {
                "action": {"work_dir": "/test/work/dir", "app_ref": "/test/app/ref", "ssh_user": "testuser"}
            }
        }
        mocker.patch("yaml.safe_load", return_value=expected_yaml_data)

        # Mock ActionConfig.model_validate
        mock_action_config = MagicMock()
        # Set up __iter__ to return key-value pairs
        mock_action_config.__iter__.return_value = [
            ("work_dir", Path("/test/work/dir")),
            ("app_ref", Path("/test/app/ref")),
            ("ssh_user", "testuser"),
            ("workunit_ref", None),
            ("filter", None),
            ("force_storage", None),
            ("read_only", None),
        ]
        mocker.patch(
            "bfabric_app_runner.actions.config_file.ActionConfig.model_validate", return_value=mock_action_config
        )

        # Input values for the validator
        input_values = {"config": "/path/to/config.yaml", "ssh_user": "override_user"}  # This should not be overridden

        # Call the validator
        result = FromConfigFile.parse_config_file(input_values)

        # Check that the validator read the config file
        mock_file.assert_called_once_with("r")

        # Check that the values are updated correctly
        assert result["config"] == "/path/to/config.yaml"
        assert result["ssh_user"] == "override_user"  # Should keep explicit value
        assert result["work_dir"] == Path("/test/work/dir")  # Should be added from config
        assert result["app_ref"] == Path("/test/app/ref")  # Should be added from config

    def test_parse_config_file_no_config_key(self, mocker):
        """Test parse_config_file method when no config key is present"""
        # Input values without config key
        input_values = {"ssh_user": "test_user", "work_dir": "/some/dir"}

        # Call the validator
        result = FromConfigFile.parse_config_file(input_values)

        # The input should be returned unchanged
        assert result == input_values

    def test_parse_config_file_non_dict_input(self, mocker):
        """Test parse_config_file method with non-dict input"""
        # Call the validator with a non-dict input
        input_values = "not a dict"
        result = FromConfigFile.parse_config_file(input_values)

        # The input should be returned unchanged
        assert result == input_values
