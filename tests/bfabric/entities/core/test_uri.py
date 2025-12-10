import pytest
from pydantic import HttpUrl, BaseModel

from bfabric.entities.core.uri import EntityUri, EntityUriComponents, GroupedUris
from bfabric.entities.core.uri import _parse_uri_components


class TestEntityUri:
    @pytest.mark.parametrize(
        "uri",
        [
            "https://fgcz-bfabric.uzh.ch/bfabric/project/show.html?id=3000",
            "http://localhost:8080/bfabric/project/show.html?id=3000",
        ],
    )
    def test_valid(self, uri):
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

    @pytest.mark.parametrize(
        "bfabric_instance", ["https://bfabric.example.com/bfabric/", "https://bfabric.example.com/bfabric"]
    )
    def test_from_components(self, bfabric_instance: str):
        entity_uri = EntityUri.from_components(bfabric_instance, "dataset", 1234)
        expected_uri = "https://bfabric.example.com/bfabric/dataset/show.html?id=1234"
        assert entity_uri == expected_uri
        assert isinstance(entity_uri, EntityUri)


class TestEntityUriComponents:
    @pytest.mark.parametrize(
        "bfabric_instance",
        [
            "https://fgcz-bfabric.uzh.ch/bfabric/",
            "https://bfabric.example.com/bfabric/",
            "http://localhost:8080/bfabric/",
        ],
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

    @pytest.mark.parametrize(
        "bfabric_instance", ["https://bfabric.example.com/bfabric/", "https://bfabric.example.com/bfabric"]
    )
    def test_as_uri(self, bfabric_instance):
        components = EntityUriComponents(bfabric_instance=bfabric_instance, entity_type="project", entity_id=3000)
        entity_uri = components.as_uri()
        assert entity_uri == "https://bfabric.example.com/bfabric/project/show.html?id=3000"
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


class TestGroupedUris:
    def test_from_uris_groups_by_type_and_instance(self):
        """Test grouping URIs by both entity type and B-Fabric instance."""
        # Create URIs with different types and instances
        uri1 = EntityUri("https://instance1.example.org/bfabric/project/show.html?id=100")
        uri2 = EntityUri("https://instance1.example.org/bfabric/project/show.html?id=200")
        uri3 = EntityUri("https://instance1.example.org/bfabric/user/show.html?id=1")
        uri4 = EntityUri("https://instance2.example.org/bfabric/project/show.html?id=300")
        uri5 = EntityUri("https://instance2.example.org/bfabric/user/show.html?id=2")

        grouped = GroupedUris.from_uris([uri1, uri2, uri3, uri4, uri5])

        # Should have 4 groups: (instance1, project), (instance1, user), (instance2, project), (instance2, user)
        assert len(grouped.groups) == 4

        # Verify groups contain correct URIs
        groups_dict = {(key.bfabric_instance, key.entity_type): uris for key, uris in grouped.items()}

        assert groups_dict[("https://instance1.example.org/bfabric/", "project")] == [uri1, uri2]
        assert groups_dict[("https://instance1.example.org/bfabric/", "user")] == [uri3]
        assert groups_dict[("https://instance2.example.org/bfabric/", "project")] == [uri4]
        assert groups_dict[("https://instance2.example.org/bfabric/", "user")] == [uri5]
