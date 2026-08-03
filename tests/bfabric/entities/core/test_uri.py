import pytest
from pydantic import HttpUrl, BaseModel

from bfabric.entities.core.uri import EntityUri, EntityUriComponents, GroupedUris
from bfabric.entities.core.uri import _parse_uri_components

CANONICAL_URI = "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=346001"


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

    @pytest.mark.parametrize(
        "uri",
        [
            f"{CANONICAL_URI}&tab=details",
            f"{CANONICAL_URI}#tab",
            f"{CANONICAL_URI}&id=346001",
        ],
    )
    def test_non_canonical_rejected_with_hint(self, uri):
        """The constructor stays strict, but points at the lenient entry point."""
        with pytest.raises(ValueError, match="EntityUri.normalize"):
            EntityUri(uri)

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


class TestNormalize:
    @pytest.mark.parametrize(
        "url",
        [
            CANONICAL_URI,
            f"{CANONICAL_URI}&tab=details",
            "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?tab=details&id=346001",
            f"{CANONICAL_URI}#tab",
            f"{CANONICAL_URI}&id=346001",
            "https://FGCZ-Bfabric.UZH.ch/bfabric/workunit/show.html?id=346001",
            "https://fgcz-bfabric.uzh.ch:443/bfabric/workunit/show.html?id=346001",
        ],
    )
    def test_normalizes_to_canonical(self, url):
        uri = EntityUri.normalize(url)
        assert uri == CANONICAL_URI
        assert isinstance(uri, EntityUri)

    def test_keeps_explicit_non_default_port(self):
        uri = EntityUri.normalize("http://localhost:8080/bfabric/project/show.html?id=3000&tab=details")
        assert uri == "http://localhost:8080/bfabric/project/show.html?id=3000"

    def test_idempotent_on_entity_uri(self):
        assert EntityUri.normalize(EntityUri(CANONICAL_URI)) == CANONICAL_URI

    def test_components(self):
        components = EntityUri.normalize(f"{CANONICAL_URI}&tab=details").components
        assert components.bfabric_instance == HttpUrl("https://fgcz-bfabric.uzh.ch/bfabric/")
        assert components.entity_type == "workunit"
        assert components.entity_id == 346001

    def test_keys_dict_like_canonical(self):
        """Normalization is what makes a pasted URL usable as an EntityResult / cache key."""
        uri = EntityUri.normalize(f"{CANONICAL_URI}&tab=details")
        assert hash(uri) == hash(EntityUri(CANONICAL_URI))
        assert len({uri, EntityUri(CANONICAL_URI)}) == 1

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com/bfabric/workunit/show.html?id=346001",
            "ftp://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=346001",
            "https://user:pw@fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=346001",
            "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html",
            "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?tab=details",
            "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=abc",
            "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=0",
            "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.html?id=346001&id=346002",
            "https://fgcz-bfabric.uzh.ch/bfabric/workunit/show.htm?id=346001",
            "https://fgcz-bfabric.uzh.ch/lims/bfabric/workunit/show.html?id=346001",
            "https://fgcz-bfabric.uzh.ch/bfabric/Workunit/show.html?id=346001",
            "https://example.com/invalid/uri",
            "not-a-url",
            "",
        ],
    )
    def test_invalid(self, url):
        with pytest.raises(ValueError):
            EntityUri.normalize(url)


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
