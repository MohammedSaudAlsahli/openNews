import asyncio
import json
from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from eis_engine import model_catalog as discovery
from eis_engine.providers import read_credentials, catalog
from eis_engine.contracts import Failure


def profile(tmp_path, key="openai", config=None, credentials=None):
    directory = tmp_path / ".providers"
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / f"{uuid4()}.json"
    path.write_text(json.dumps(credentials or {"api_key":"secret-test-only"}))
    path.chmod(0o600)
    return {"provider_key":key, "credential_path":str(path), "config_json":json.dumps(config or {})}


def mock_http(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(discovery.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))


def test_credential_file_permissions_and_no_symlink(tmp_path):
    p = profile(tmp_path)
    assert read_credentials(p)["api_key"] == "secret-test-only"
    file = Path(p["credential_path"])
    file.chmod(0o644)
    with pytest.raises(Failure): read_credentials(p)
    file.chmod(0o600)
    original = file.with_suffix(".backup")
    file.rename(original)
    file.symlink_to(original)
    with pytest.raises(Failure): read_credentials(p)


def test_missing_local_credentials_are_optional_but_remote_are_not(tmp_path):
    p = profile(tmp_path, "ollama")
    Path(p["credential_path"]).unlink()
    assert read_credentials(p) == {}
    p["provider_key"] = "openai"
    with pytest.raises(Failure): read_credentials(p)


def test_credentials_reject_unknown_secret_fields_without_echo(tmp_path):
    p = profile(tmp_path, credentials={"malicious":"never-echo-this"})
    with pytest.raises(Failure) as caught: read_credentials(p)
    assert "never-echo-this" not in str(caught.value)


def test_all_pinned_adapters_have_a_discovery_strategy():
    entries = catalog()["providers"]
    assert len(entries) == 69
    assert all(discovery.strategy(x["id"]) for x in entries)
    assert all(x["status"] == "ready" for x in entries)


def test_openai_pagination_and_fixed_origin(tmp_path, monkeypatch):
    seen = []
    def handler(request):
        seen.append(request)
        assert request.url.host == "api.openai.com"
        assert request.headers["Authorization"] == "Bearer secret-test-only"
        if len(seen) == 1: return httpx.Response(200, json={"data":[{"id":"model-a"}], "has_more":True, "last_id":"model-a"})
        assert request.url.params["after"] == "model-a"
        return httpx.Response(200, json={"data":[{"id":"model-b"}]})
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path)))
    assert [x["id"] for x in result["models"]] == ["model-a", "model-b"]


def test_redirect_never_receives_token(tmp_path, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location":"https://untrusted.invalid/models"})
    mock_http(monkeypatch, handler)
    with pytest.raises(Failure): asyncio.run(discovery.discover(profile(tmp_path)))
    assert len(calls) == 1


def test_google_pages_filters_generation_only(tmp_path, monkeypatch):
    def handler(request):
        assert "key" not in request.url.params
        assert request.headers["x-goog-api-key"] == "secret-test-only"
        if request.url.params.get("pageToken"):
            return httpx.Response(200,json={"models":[{"name":"models/gemini-next", "supportedGenerationMethods":["generateContent"]}]})
        return httpx.Response(200,json={"models":[{"name":"models/embedding", "supportedGenerationMethods":["embedContent"]}], "nextPageToken":"page2"})
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path, "google")))
    assert [x["id"] for x in result["models"]] == ["gemini-next"]


def test_anthropic_pages(tmp_path, monkeypatch):
    def handler(request):
        assert request.headers["x-api-key"] == "secret-test-only"
        after = request.url.params.get("after_id")
        return httpx.Response(200,json={"data":[{"id":"second" if after else "first"}], "has_more":not bool(after), "last_id":"first"})
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path, "anthropic")))
    assert len(result["models"]) == 2


def test_ollama_installed_survives_public_library_offline(tmp_path, monkeypatch):
    def handler(request):
        if request.url.host == "ollama.com": raise httpx.ConnectError("secret-test-only")
        return httpx.Response(200,json={"models":[{"name":"local:7b"}]})
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path, "ollama")))
    assert result["models"] == [{"id":"local:7b", "name":"local:7b", "available":True}]
    assert "تعذّر" in result["source"]


def test_ollama_public_is_not_installed_and_has_no_token(tmp_path, monkeypatch):
    def handler(request):
        if request.url.host == "ollama.com":
            assert "Authorization" not in request.headers
            return httpx.Response(200,text='<a href="/library/newly-published">model</a>')
        return httpx.Response(200,json={"models":[{"name":"local:7b"}]})
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path, "ollama")))
    assert {x["id"]:x["available"] for x in result["models"]} == {"local:7b":True, "newly-published":False}


def test_perplexity_reads_official_current_catalog_not_static_ids(tmp_path, monkeypatch):
    def handler(request):
        assert request.url.host == "docs.perplexity.ai"
        assert "Authorization" not in request.headers
        return httpx.Response(200,text='export const PRICING = {"sonar":{"models":[{"id":"sonar-brand-new","label":"New Sonar"}]}};')
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path, "perplexity")))
    assert result["models"][0]["id"] == "sonar-brand-new"


def test_azure_returns_deployment_names_and_rejects_foreign_pagination(tmp_path, monkeypatch):
    config = {"subscription_id":"s", "resource_group":"r", "account_name":"a"}
    def handler(request):
        assert request.url.host == "management.azure.com"
        assert request.headers["Authorization"] == "Bearer arm-secret"
        return httpx.Response(200,json={"value":[{"name":"my-deployment", "properties":{"provisioningState":"Succeeded"}}]})
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path, "azure-openai", config, {"azure_management_token":"arm-secret"})))
    assert result["models"][0] == {"id":"my-deployment", "name":"my-deployment", "available":True}


def test_error_does_not_echo_provider_response_or_token(tmp_path, monkeypatch):
    mock_http(monkeypatch, lambda request: httpx.Response(500,text="secret-test-only private provider diagnostic"))
    with pytest.raises(Failure) as caught: asyncio.run(discovery.discover(profile(tmp_path)))
    assert "secret-test-only" not in str(caught.value)


def test_public_openrouter_without_key(tmp_path, monkeypatch):
    def handler(request):
        assert request.url.host == "openrouter.ai"
        assert "Authorization" not in request.headers
        return httpx.Response(200,json={"data":[{"id":"new/provider-model"}]})
    mock_http(monkeypatch, handler)
    p = profile(tmp_path, "openrouter")
    Path(p["credential_path"]).write_text("{}")
    result = asyncio.run(discovery.discover(p))
    assert result["models"][0]["id"] == "new/provider-model"


def test_ibm_official_pagination(tmp_path, monkeypatch):
    def handler(request):
        assert request.url.host == "eu-de.ml.cloud.ibm.com"
        if request.url.params.get("start"):
            return httpx.Response(200,json={"resources":[{"model_id":"ibm/new"}]})
        return httpx.Response(200,json={"resources":[{"model_id":"ibm/first"}], "next":{"href":"/ml/v1/foundation_model_specs?version=2024-05-31&start=next"}})
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path, "ibm")))
    assert len(result["models"]) == 2


def test_bedrock_lists_active_inference_profiles_across_pages(tmp_path, monkeypatch):
    import boto3
    class Client:
        def list_foundation_models(self):
            return {"modelSummaries":[{"modelId":"anthropic.base", "providerName":"Anthropic", "outputModalities":["TEXT"]}]}
        def list_inference_profiles(self, **kwargs):
            if kwargs.get("nextToken"):
                return {"inferenceProfileSummaries":[{"inferenceProfileId":"global.anthropic.new", "status":"ACTIVE"}]}
            return {"inferenceProfileSummaries":[], "nextToken":"page2"}
        def close(self): pass
    monkeypatch.setattr(boto3, "client", lambda *a, **kw:Client())
    p = profile(tmp_path, "aws-claude", {"aws_region":"us-east-1"}, {"aws_access_key_id":"synthetic", "aws_secret_access_key":"synthetic"})
    result = asyncio.run(discovery.discover(p))
    assert {x["id"] for x in result["models"]} == {"anthropic.base", "global.anthropic.new"}

@pytest.mark.parametrize('key', ['ollama', 'ollama-responses'])
def test_ollama_cloud_only_lists_exact_cloud_ids(tmp_path, monkeypatch, key):
    calls = []
    def handler(request):
        calls.append(request)
        assert str(request.url) == 'https://ollama.com/api/tags'
        assert request.headers['Authorization'] == 'Bearer secret-test-only'
        return httpx.Response(200, json={'models': [{'name': 'gemma4:31b'}, {'model': 'cloud-model:latest'}]})
    mock_http(monkeypatch, handler)
    result = asyncio.run(discovery.discover(profile(tmp_path, key, {'host': 'https://ollama.com/v1'})))
    assert len(calls) == 1
    assert {row['id'] for row in result['models']} == {'gemma4:31b', 'cloud-model:latest'}
    assert all(row['available'] for row in result['models'])
    assert result['source'] == 'https://ollama.com/api/tags — Ollama Cloud'

@pytest.mark.parametrize('key', ['ollama', 'ollama-responses'])
def test_ollama_factory_cloud_auth_and_local_environment_isolation(tmp_path, monkeypatch, key):
    from eis_engine.providers import ModelFactory
    monkeypatch.setenv('OLLAMA_API_KEY', 'ambient-must-not-be-used')
    monkeypatch.setenv('OLLAMA_HOST', 'https://unexpected.invalid')
    p = profile(tmp_path, key, {'host': 'https://ollama.com'})
    p['model_id'] = 'gemma4:31b'
    model = ModelFactory().create(p)
    assert model.id == 'gemma4:31b'
    params = model._get_client_params()
    if key == 'ollama':
        assert params['host'] == 'https://ollama.com'
        assert params['headers']['authorization'] == 'Bearer secret-test-only'
    else:
        assert params['base_url'] == 'https://ollama.com/v1'
        assert params['api_key'] == 'secret-test-only'
    Path(p['credential_path']).write_text('{}')
    with pytest.raises(Failure) as caught: ModelFactory().create(p)
    assert caught.value.code == 'AUTH_REQUIRED'
    p['config_json'] = '{}'
    local = ModelFactory().create(p)
    assert local.host == 'http://127.0.0.1:11434'
    assert local.api_key is None
    params = local._get_client_params()
    assert 'ambient-must-not-be-used' not in repr(params)
    assert 'unexpected.invalid' not in repr(params)


def test_ollama_cloud_public_discovery_without_saved_key(tmp_path, monkeypatch):
    def handler(request):
        assert str(request.url) == 'https://ollama.com/api/tags'
        assert 'Authorization' not in request.headers
        return httpx.Response(200, json={'models': [{'name': 'public-cloud:large'}]})
    mock_http(monkeypatch, handler)
    p = profile(tmp_path, 'ollama', {'host': 'https://ollama.com'})
    Path(p['credential_path']).unlink()
    assert asyncio.run(discovery.discover(p))['models'][0]['id'] == 'public-cloud:large'


def test_ollama_cloud_rejects_insecure_host_before_auth(tmp_path, monkeypatch):
    def handler(request):
        pytest.fail('insecure endpoint must not receive an API key')
    mock_http(monkeypatch, handler)
    with pytest.raises(Failure):
        asyncio.run(discovery.discover(profile(tmp_path, 'ollama', {'host': 'http://ollama.com'})))
