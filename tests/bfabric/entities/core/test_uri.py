import pytest
from pydantic import HttpUrl, BaseModel

from bfabric.entities.core.uri import EntityUri
from bfabric.entities.core.uri import _parse_uri_components


class TestEntityUri:
    def test_valid(self):
        uri = "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=3000"
        entity_uri = EntityUri(uri)
        assert entity_uri == uri
        assert isinstance(entity_uri, EntityUri)

    def test_invalid(self):
        uri = "https://example.com/invalid/uri"
        with pytest.raises(ValueError) as error:
            EntityUri(uri)
        assert "Invalid Entity URI" in str(error.value)

    def test_components_property(self):
        uri = "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=3000"
        entity_uri = EntityUri(uri)
        components = entity_uri.components
        assert components.bfabric_instance == HttpUrl("https://fgcz-bfabric.uzh.ch/bfabric/")
        assert components.entity_type == "project"
        assert components.entity_id == 3000


class TestEntityUriComponents:
    @pytest.mark.parametrize(
        "bfabric_instance", ["https://fgcz-bfabric.uzh.ch/bfabric/", "https://bfabric.example.com/bfabric/"]
    )
    def test_valid(self, bfabric_instance):
        uri = f"{bfabric_instance}project/show.html?id=3000"
        parsed = _parse_uri_components(uri)
        assert parsed.bfabric_instance == HttpUrl(bfabric_instance)
        assert parsed.entity_type == "project"
        assert parsed.entity_id == 3000

    @pytest.mark.parametrize(
        "uri",
        [
            "https://fgcz-bfabric.uzh.ch/project/show.html?id=3000",
            "https://fgcz-bfabric.uzh.ch/Project/show.html?id=3000",
            "https://fgcz-bfabric.uzh.ch/bfabric/show.html?id=3000",
            "http://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=3000",
        ],
    )
    def test_invalid(self, uri):
        with pytest.raises(ValueError):
            _parse_uri_components(uri)

    def test_as_uri(self):
        components = _parse_uri_components("https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=3000")
        entity_uri = components.as_uri()
        assert entity_uri == "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=3000"
        assert isinstance(entity_uri, EntityUri)


class TestPydanticModel:
    class MockModel(BaseModel):
        uri: EntityUri

    def test_validate(self):
        uri = "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=3000"
        model = self.MockModel(uri=uri)
        assert model.uri == uri
        assert isinstance(model.uri, EntityUri)

    def test_dump(self):
        uri = "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=3000"
        model = self.MockModel(uri=uri)
        dumped = model.model_dump()
        assert dumped["uri"] == uri
