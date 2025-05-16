import pytest

from bfabric.entities import Application


@pytest.mark.parametrize(
    "technology_value, expected_technology",
    [
        (["Proteomics", "Metabolomics/Biophysics"], "Metabolomics_Biophysics"),
        (["Metabolomics/Biophysics", "Proteomics"], "Metabolomics_Biophysics"),
        (["Metabolomics/Biophysics"], "Metabolomics_Biophysics"),
        (["Proteomics"], "Proteomics"),
        ("Proteomics", "Proteomics"),
    ],
)
def test_technology_folder_name(technology_value, expected_technology):
    data_dict = {"technology": technology_value}
    application = Application(data_dict=data_dict, client=None)
    assert application.technology_folder_name == expected_technology
