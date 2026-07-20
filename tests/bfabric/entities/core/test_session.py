import pytest

from bfabric import Bfabric
from bfabric.entities.core.session import BfabricSession, _reset_session, get_session
from bfabric.entities.core.uri import EntityUri

INSTANCE_A = "https://a.example.org/bfabric/"
INSTANCE_B = "https://b.example.org/bfabric/"


@pytest.fixture
def client_a(mocker):
    return mocker.MagicMock(spec=Bfabric, config=mocker.MagicMock(base_url=INSTANCE_A))


@pytest.fixture
def client_b(mocker):
    return mocker.MagicMock(spec=Bfabric, config=mocker.MagicMock(base_url=INSTANCE_B))


@pytest.fixture(autouse=True)
def _clean_session():
    _reset_session()
    yield
    _reset_session()


class TestAmbientContext:
    def test_get_session_raises_when_none_active(self):
        with pytest.raises(LookupError, match="No active BfabricSession"):
            get_session()

    def test_with_sets_and_restores(self, client_a):
        session = BfabricSession(client_a)
        with session as active:
            assert active is session
            assert get_session() is session
        with pytest.raises(LookupError):
            get_session()

    def test_nesting_merges_by_instance(self, client_a, client_b):
        outer = BfabricSession(client_a)
        inner = BfabricSession(client_b)
        with outer, inner:
            # inner resolves its own instance and falls back to outer's for the other
            assert inner._reader_for(INSTANCE_B) is inner._readers[INSTANCE_B]
            assert inner._reader_for(INSTANCE_A) is outer._readers[INSTANCE_A]
            assert get_session() is inner
        assert True  # both contexts exited cleanly

    def test_reentry_same_session_restores_cleanly(self, client_a):
        # ``client.reader`` is a cached_property, so a nested ``with client.reader:`` (e.g. the
        # app-runner resolver running inside the @use_client CLI decorator) re-enters the *same*
        # session object. Both exits must succeed and the context must be fully cleared.
        session = BfabricSession(client_a)
        with session:
            with session:
                assert get_session() is session
            # inner exit must not clear the still-active outer context
            assert get_session() is session
        # outer exit restores to no-session and must not raise on a reused token
        with pytest.raises(LookupError):
            get_session()


class TestConstruction:
    def test_single_client(self, client_a):
        assert BfabricSession(client_a).instances == [INSTANCE_A]

    def test_multiple_clients(self, client_a, client_b):
        assert set(BfabricSession([client_a, client_b]).instances) == {INSTANCE_A, INSTANCE_B}

    def test_reader_for_unknown_instance_raises(self, client_a):
        with pytest.raises(LookupError, match="No B-Fabric connection registered"):
            BfabricSession(client_a)._reader_for(INSTANCE_B)

    def test_default_instance_ambiguous_raises(self, client_a, client_b):
        with pytest.raises(LookupError, match="pass bfabric_instance="):
            BfabricSession([client_a, client_b])._default_instance()

    def test_read_only_no_write_methods(self, client_a):
        session = BfabricSession(client_a)
        assert not hasattr(session, "save")
        assert not hasattr(session, "delete")


class TestRouting:
    def test_read_uris_routes_each_instance_to_its_reader(self, mocker, client_a, client_b):
        session = BfabricSession([client_a, client_b])
        reader_a, reader_b = mocker.MagicMock(name="reader_a"), mocker.MagicMock(name="reader_b")
        session._readers = {INSTANCE_A: reader_a, INSTANCE_B: reader_b}

        uri_a = EntityUri(f"{INSTANCE_A}project/show.html?id=1")
        uri_b = EntityUri(f"{INSTANCE_B}project/show.html?id=2")
        ent_a, ent_b = mocker.MagicMock(name="ent_a"), mocker.MagicMock(name="ent_b")
        reader_a.read_uris.return_value = {uri_a: ent_a}
        reader_b.read_uris.return_value = {uri_b: ent_b}

        result = session.read_uris([uri_a, uri_b])

        assert result == {uri_a: ent_a, uri_b: ent_b}
        assert list(reader_a.read_uris.call_args.args[0]) == [uri_a]
        assert list(reader_b.read_uris.call_args.args[0]) == [uri_b]

    def test_query_routes_to_named_instance(self, mocker, client_a, client_b):
        session = BfabricSession([client_a, client_b])
        reader_a, reader_b = mocker.MagicMock(name="reader_a"), mocker.MagicMock(name="reader_b")
        session._readers = {INSTANCE_A: reader_a, INSTANCE_B: reader_b}
        reader_b.query.return_value = {"uri": "entity"}

        result = session.query("workunit", {"status": "processing"}, bfabric_instance=INSTANCE_B)

        assert result == {"uri": "entity"}
        reader_b.query.assert_called_once()
        reader_a.query.assert_not_called()

    def test_read_id_uses_default_instance(self, mocker, client_a):
        session = BfabricSession(client_a)
        reader_a = mocker.MagicMock(name="reader_a")
        session._readers = {INSTANCE_A: reader_a}
        uri = EntityUri(f"{INSTANCE_A}workunit/show.html?id=7")
        entity = mocker.MagicMock(name="entity")
        reader_a.read_uris.return_value = {uri: entity}

        assert session.read_id("workunit", 7) is entity


class TestCacheScoping:
    def test_cache_entities_pushed_and_popped(self, client_a):
        session = BfabricSession(client_a)
        assert len(session._cache._stack) == 0
        with session.cache_entities("workunit", max_size=5):
            assert len(session._cache._stack) == 1
        assert len(session._cache._stack) == 0

    def test_free_cache_entities_delegates_to_active_session(self, client_a):
        from bfabric.entities.cache.context import cache_entities

        session = BfabricSession(client_a)
        with session, cache_entities("workunit"):
            assert len(session._cache._stack) == 1
        assert len(session._cache._stack) == 0

    def test_free_cache_entities_without_session_raises(self):
        from bfabric.entities.cache.context import cache_entities

        with pytest.raises(LookupError), cache_entities("workunit"):
            pass
