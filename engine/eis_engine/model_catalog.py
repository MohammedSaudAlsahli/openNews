"""Live provider model discovery; IDs come from remote catalogs, never a bundled model list.

OpenAI-compatible adapters use their pinned Agno base URL and /models. A server may
not implement that endpoint; its capability error is explicit, never a fake list.
"""
import asyncio
import json
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit, quote, urljoin
import httpx
from .contracts import Failure
from .providers import catalog, read_credentials, google_credentials, ollama_cloud

DEFAULT_BASES = {
    "openai": "https://api.openai.com/v1", "openai-chat": "https://api.openai.com/v1", "openai-responses": "https://api.openai.com/v1",
    "cerebras": "https://api.cerebras.ai/v1", "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1", "meta": "https://api.llama.com/v1",
    "vllm": "http://127.0.0.1:8000/v1", "ollama": "http://127.0.0.1:11434", "ollama-responses": "http://127.0.0.1:11434",
    "langdb": "https://api.us-east-1.langdb.ai", "tuning-engines": "https://api.tuningengines.com/v1",
}
SPECIAL = {
    "google-oauth": "vertex-oauth", "openai-chatgpt": "chatgpt-oauth",
    "anthropic": "anthropic", "azure-foundry-claude": "anthropic-foundry", "google": "google", "google-interactions": "google",
    "ollama": "ollama", "ollama-responses": "ollama", "aws-bedrock": "bedrock", "aws-claude": "bedrock",
    "vertexai-claude": "vertex", "azure-openai": "azure", "azure-openai-responses": "azure", "azure-ai-foundry": "azure",
    "cloudflare": "cloudflare", "cohere": "cohere", "huggingface": "huggingface", "ibm": "ibm", "litellm": "litellm-published", "perplexity": "perplexity-published",
}


def strategy(provider):
    return SPECIAL.get(provider, "openai-compatible")


def safe_base(value):
    parts = urlsplit(value)
    if parts.username or parts.password or parts.query or parts.fragment or not parts.hostname:
        raise Failure("VALIDATION_ERROR", "عنوان اكتشاف النماذج غير صالح.")
    if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}):
        raise Failure("VALIDATION_ERROR", "استخدم HTTPS للمزود أو عنوان خادم محلي.")
    return value.rstrip("/")


def rows(items, available=True):
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        identifier = item.get("id") or item.get("model") or item.get("name")
        if not isinstance(identifier, str) or not identifier or len(identifier) > 300:
            continue
        result.append({"id": identifier, "name": item.get("display_name") or item.get("displayName") or identifier, "available": available})
    return result


async def request(client, url, headers=None, params=None, raw=False):
    response = await client.get(url, headers=headers or {}, params=params)
    if response.status_code == 401:
        raise Failure("AUTH_REQUIRED", "تعذّر الوصول إلى دليل النماذج. راجع بيانات الاعتماد وصلاحيات الحساب.")
    if response.status_code == 403:
        raise Failure("PERMISSION_DENIED", "المزوّد رفض صلاحية الوصول إلى قائمة النماذج؛ راجع صلاحيات الحساب.")
    if response.status_code >= 500:
        raise Failure("PROVIDER_UNAVAILABLE", "خدمة المزوّد غير متاحة مؤقتًا؛ بيانات الدخول محفوظة.")
    if response.status_code == 429:
        raise Failure("RATE_LIMITED", "وصل تحديث النماذج إلى حد الطلبات. حاول لاحقًا.")
    if response.is_redirect or response.status_code in {404, 405, 501}:
        raise Failure("DISCOVERY_UNAVAILABLE", "لا يوفّر عنوان المزود هذا واجهة قائمة نماذج متوافقة. راجع إعدادات الخادم أو حدّث التطبيق لتحديث مهايئ الدليل.")
    response.raise_for_status()
    if len(response.content) > 15_000_000:
        raise Failure("DISCOVERY_UNAVAILABLE", "دليل المزود أكبر من الحد المسموح لهذه النسخة.")
    return response.text if raw else response.json()


class OllamaLibrary(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = set()
    def handle_starttag(self, tag, attrs):
        if tag != "a": return
        href = dict(attrs).get("href", "")
        match = re.fullmatch(r"/library/([a-zA-Z0-9_.:-]+)", href)
        if match: self.names.add(match.group(1))


async def _bedrock(config, secrets, claude=False):
    import boto3
    from botocore.config import Config
    region = config.get("aws_region") or config.get("region_name") or config.get("region")
    if not region or not secrets.get("aws_access_key_id") or not secrets.get("aws_secret_access_key"):
        raise Failure("AUTH_REQUIRED", "أضف منطقة AWS ومفتاح الوصول والمفتاح السري لتحديث الدليل.")
    def fetch():
        client = boto3.client("bedrock", region_name=region,
            aws_access_key_id=secrets["aws_access_key_id"], aws_secret_access_key=secrets["aws_secret_access_key"],
            aws_session_token=secrets.get("aws_session_token"), config=Config(connect_timeout=10, read_timeout=20, retries={"max_attempts": 1}))
        try:
            models = client.list_foundation_models().get("modelSummaries", [])
            result = [{"id": x["modelId"], "name": x.get("modelName", x["modelId"]), "available": True}
                    for x in models if "TEXT" in x.get("outputModalities", []) and (not claude or x.get("providerName") == "Anthropic")]
            page, seen = "", set()
            for _ in range(100):
                response = client.list_inference_profiles(**({"nextToken": page} if page else {}))
                for item in response.get("inferenceProfileSummaries", []):
                    identifier = item.get("inferenceProfileId")
                    if identifier and item.get("status") == "ACTIVE" and (not claude or "anthropic" in identifier or any("anthropic" in m.get("modelArn", "") for m in item.get("models", []))):
                        result.append({"id":identifier, "name":item.get("inferenceProfileName", identifier), "available":True})
                page = response.get("nextToken")
                if not page: return result
                if page in seen: break
                seen.add(page)
            raise Failure("DISCOVERY_UNAVAILABLE", "لم تكتمل صفحات ملفات استدلال AWS.")
        finally: client.close()
    return await asyncio.to_thread(fetch)


async def _vertex(client, config, secrets, publisher="anthropic", auth=None):
    if auth is None:
        credential = google_credentials(secrets)
        def token():
            from google.auth.transport.requests import Request
            credential.refresh(Request())
            return credential.token
        auth = await asyncio.to_thread(token)
    region = config.get("region") or config.get("location") or "us-central1"
    if not re.fullmatch(r"[a-z0-9-]+", region): raise Failure("VALIDATION_ERROR", "منطقة Google غير صالحة.")
    url = f"https://{region}-aiplatform.googleapis.com/v1/publishers/{publisher}/models"
    result, page, seen = [], "", set()
    for _ in range(100):
        data = await request(client, url, {"Authorization": f"Bearer {auth}"}, {"pageSize": 100, **({"pageToken": page} if page else {})})
        for item in data.get("publisherModels", data.get("models", [])):
            identifier = item.get("name", "").split("/models/")[-1]
            if identifier: result.append({"id": identifier, "name": item.get("displayName", identifier), "available": True})
        page = data.get("nextPageToken")
        if not page: return result
        if page in seen: break
        seen.add(page)
    raise Failure("DISCOVERY_UNAVAILABLE", "لم تكتمل صفحات دليل Google. لم تُحفظ قائمة ناقصة.")


async def discover(profile):
    """Return live IDs; available means selectable, not verified entitlement. Uninstalled Ollama entries are not selectable."""
    try:
        return await _discover(profile)
    except Failure:
        raise
    except httpx.HTTPError:
        raise Failure("NETWORK_ERROR", "تعذّر الوصول إلى المزوّد. بيانات دخولك محفوظة؛ تحقق من الشبكة وحاول مجددًا.") from None
    except Exception:
        # HTTP/SDK exception messages can contain signed URLs, tokens, or request headers.
        raise Failure("DISCOVERY_UNAVAILABLE", "تعذّر تحديث دليل النماذج. راجع إعدادات المزود والاتصال ثم حاول مجددًا.") from None


async def _discover(profile):
    key = profile["provider_key"]
    if key == "openai-chatgpt":
        from .chatgpt_auth import discover_models
        return await discover_models(profile)
    if key == "google-oauth":
        from .google_auth import access_token
        config = json.loads(profile["config_json"])
        token = await access_token(profile)
        async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as client:
            models = await _vertex(client, config, {}, "google", auth=token)
        return {"models":models, "source":"Google Vertex AI — published models; verify project access before use"}
    entry = next((x for x in catalog()["providers"] if x["id"] == key), None)
    if not entry: raise Failure("MODEL_UNSUPPORTED", "المزود غير موجود في دليل Agno المثبت.")
    config = json.loads(profile.get("config_json", "{}"))
    secrets = read_credentials(profile)
    token = secrets.get("api_key", "")
    route = strategy(key)
    headers = {"Authorization": "Bearer " + token} if token else {}
    result, source = [], ""
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as client:
        if route == "bedrock":
            result = await _bedrock(config, secrets, key == "aws-claude")
            source = "AWS Bedrock ListFoundationModels + ListInferenceProfiles — النماذج المنشورة؛ صلاحية الحساب تحتاج اختبارًا"
        elif route == "vertex" or (key == "google" and (str(config.get("vertexai", "")).lower() == "true" or secrets.get("service_account_info"))):
            result = await _vertex(client, config, secrets, "anthropic" if route == "vertex" else "google")
            source = "Google Vertex publisher models — النماذج المنشورة؛ صلاحية الحساب تحتاج اختبارًا"
        elif route == "ollama":
            cloud = ollama_cloud(config)
            base = safe_base(config.get("host") or config.get("base_url") or DEFAULT_BASES[key])
            # Responses adapter often points at /v1 while native tags lives at root.
            base = base.removesuffix("/v1")
            data = await request(client, base + "/api/tags", headers)
            result = rows(data.get("models", []))
            if cloud:
                source = "https://ollama.com/api/tags — Ollama Cloud"
            else:
                installed = {x["id"].split(":")[0] for x in result}
                parser = OllamaLibrary()
                try:
                    parser.feed(await request(client, "https://ollama.com/library?sort=newest", raw=True))
                    if not parser.names: raise ValueError("library format")
                    result += [{"id": x, "name": x, "available": False} for x in sorted(parser.names) if x not in installed]
                    source = base + "/api/tags + https://ollama.com/library?sort=newest (المثبت محليًا / المنشور في المكتبة العامة)"
                except (Failure, httpx.HTTPError, ValueError):
                    source = base + "/api/tags — المثبت محليًا؛ تعذّر تحديث المكتبة العامة مؤقتًا"
        elif route in {"anthropic", "anthropic-foundry"}:
            base = "https://api.anthropic.com" if route == "anthropic" else config.get("base_url", "")
            if not base and config.get("resource"): base = f"https://{config['resource']}.services.ai.azure.com/anthropic"
            base = safe_base(base)
            url = base.rstrip("/").removesuffix("/v1") + "/v1/models"
            auth = {"x-api-key": token, "anthropic-version": "2023-06-01"}
            page, seen = "", set()
            for _ in range(100):
                data = await request(client, url, auth, {"limit": 100, **({"after_id": page} if page else {})})
                result += rows(data.get("data", []))
                if not data.get("has_more"): break
                page = data.get("last_id")
                if not page or page in seen: raise Failure("DISCOVERY_UNAVAILABLE", "لم تكتمل صفحات دليل المزود.")
                seen.add(page)
            else: raise Failure("DISCOVERY_UNAVAILABLE", "تجاوز دليل المزود حد الصفحات.")
            source = url
        elif route == "google":
            url, page, seen = "https://generativelanguage.googleapis.com/v1beta/models", "", set()
            for _ in range(100):
                data = await request(client, url, {"x-goog-api-key": token}, {"pageSize":100, **({"pageToken": page} if page else {})})
                for item in data.get("models", []):
                    if "generateContent" in item.get("supportedGenerationMethods", []):
                        result += rows([{**item, "id": item["name"].removeprefix("models/")}])
                page = data.get("nextPageToken")
                if not page: break
                if page in seen: raise Failure("DISCOVERY_UNAVAILABLE", "لم تكتمل صفحات دليل Google.")
                seen.add(page)
            else: raise Failure("DISCOVERY_UNAVAILABLE", "تجاوز دليل Google حد الصفحات.")
            source = url
        elif route == "cohere":
            url, page, seen = "https://api.cohere.com/v1/models", "", set()
            for _ in range(100):
                data = await request(client, url, headers, {"page_size":100, "endpoint":"chat", **({"page_token":page} if page else {})})
                result += rows(data.get("models", []))
                page = data.get("next_page_token")
                if not page: break
                if page in seen: raise Failure("DISCOVERY_UNAVAILABLE", "لم تكتمل صفحات دليل Cohere.")
                seen.add(page)
            else: raise Failure("DISCOVERY_UNAVAILABLE", "تجاوز دليل Cohere حد الصفحات.")
            source = url
        elif route == "cloudflare":
            account = config.get("account_id", "")
            if not re.fullmatch(r"[a-zA-Z0-9_-]+", account): raise Failure("VALIDATION_ERROR", "أضف معرّف حساب Cloudflare.")
            url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/models/search"
            for page in range(1, 101):
                data = await request(client, url, headers, {"page":page, "per_page":100})
                if not data.get("success", False): raise Failure("DISCOVERY_UNAVAILABLE", "تعذّر تحديث دليل Cloudflare.")
                result += rows([{**item, "id":item.get("name")} for item in data.get("result", []) if item.get("task", {}).get("name", "Text Generation") == "Text Generation"])
                if page >= data.get("result_info", {}).get("total_pages", 1): break
            else: raise Failure("DISCOVERY_UNAVAILABLE", "تجاوز دليل Cloudflare حد الصفحات.")
            source = url
        elif route == "azure":
            identifiers = [config.get(x, "") for x in ("subscription_id", "resource_group", "account_name")]
            if any(not re.fullmatch(r"[a-zA-Z0-9_.()-]+", x) for x in identifiers) or not secrets.get("azure_management_token"):
                raise Failure("AUTH_REQUIRED", "لاكتشاف عمليات نشر Azure، أضف معرّف الاشتراك ومجموعة الموارد والحساب ورمز إدارة Azure.")
            subscription, group, account = identifiers
            url = f"https://management.azure.com/subscriptions/{subscription}/resourceGroups/{group}/providers/Microsoft.CognitiveServices/accounts/{account}/deployments"
            source = url
            params = {"api-version":"2024-10-01"}
            seen = set()
            for _ in range(100):
                data = await request(client, url, {"Authorization":"Bearer " + secrets["azure_management_token"]}, params)
                for item in data.get("value", []):
                    if item.get("properties", {}).get("provisioningState") == "Succeeded":
                        result += rows([{"id":item["name"]}])
                next_url = data.get("nextLink")
                if not next_url: break
                # ARM nextLink is authoritative, but never forward authorization off its fixed origin or resource.
                if not next_url.startswith(source + "?") or next_url in seen:
                    raise Failure("DISCOVERY_UNAVAILABLE", "رابط الصفحة التالية من Azure غير متوافق.")
                seen.add(next_url)
                url, params = next_url, None
            else: raise Failure("DISCOVERY_UNAVAILABLE", "تجاوز دليل Azure حد الصفحات.")
        elif route == "ibm":
            base = safe_base(config.get("url") or "https://eu-de.ml.cloud.ibm.com")
            if not (urlsplit(base).hostname or "").endswith(".ml.cloud.ibm.com"):
                raise Failure("VALIDATION_ERROR", "أضف عنوان IBM watsonx الرسمي.")
            url = base + "/ml/v1/foundation_model_specs"
            source = url + " — النماذج المنشورة؛ صلاحية المشروع تحتاج اختبارًا"
            params, seen = {"version":"2024-05-31", "limit":200}, set()
            endpoint = url
            for _ in range(100):
                data = await request(client, url, params=params)
                result += rows([{**item, "id":item.get("model_id")} for item in data.get("resources", [])])
                next_page = data.get("next")
                if not next_page: break
                href = next_page.get("href") if isinstance(next_page, dict) else None
                if not href: raise Failure("DISCOVERY_UNAVAILABLE", "لم تكتمل صفحات دليل IBM.")
                next_url = urljoin(endpoint, href)
                if not next_url.startswith(endpoint + "?") or next_url in seen:
                    raise Failure("DISCOVERY_UNAVAILABLE", "رابط الصفحة التالية من IBM غير متوافق.")
                seen.add(next_url)
                url, params = next_url, None
            else: raise Failure("DISCOVERY_UNAVAILABLE", "تجاوز دليل IBM حد الصفحات.")
        elif route == "huggingface":
            url = "https://router.huggingface.co/v1/models"
            data = await request(client, url, headers)
            result = rows(data.get("data", []))
            source = url
        elif route == "perplexity-published":
            url = "https://docs.perplexity.ai/docs/getting-started/pricing.md"
            text = await request(client, url, raw=True)
            marker = "export const PRICING = "
            start = text.index(marker) + len(marker)
            data, _ = json.JSONDecoder().raw_decode(text[start:])
            result = rows([{**item, "display_name":item.get("label")} for item in data["sonar"]["models"]])
            source = url + " — دليل Sonar المنشور؛ صلاحية المفتاح تحتاج اختبارًا"
        elif route == "litellm-published":
            url = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
            data = await request(client, url)
            result = rows([{"id":identifier} for identifier, metadata in data.items() if isinstance(metadata, dict) and metadata.get("mode") in {"chat", "completion", "responses"}], available=True)
            source = url + " — دليل LiteLLM المنشور؛ كل مزود يحتاج اعتماده"
        else:
            base = config.get("base_url") or config.get("api_base") or entry.get("default_base_url") or DEFAULT_BASES.get(key, "")
            if not base: raise Failure("VALIDATION_ERROR", "أضف عنوان API لهذا المهايئ لتحديث دليل نماذجه.")
            if key == "langdb" and not config.get("base_url"):
                project = config.get("project_id", "")
                if not re.fullmatch(r"[a-zA-Z0-9_-]+", project): raise Failure("VALIDATION_ERROR", "أضف معرّف مشروع LangDB.")
                base = (config.get("base_host_url") or base).rstrip("/") + "/" + project + "/v1"
            # Agno's InternLM default is a completion URL, not its API root.
            base = safe_base(base).removesuffix("/chat/completions")
            url = base + "/models"
            if key == "portkey": headers = {"x-portkey-api-key":secrets.get("portkey_api_key", token)}
            params, seen = {}, set()
            for _ in range(100):
                data = await request(client, url, headers, params)
                items = data if isinstance(data, list) else data.get("data", data.get("models", []))
                result += rows(items)
                if not isinstance(data, dict): break
                cursor = data.get("next_page_token") or data.get("nextPageToken")
                if cursor:
                    parameter = "page_token" if "next_page_token" in data else "pageToken"
                elif data.get("has_more"):
                    cursor = data.get("last_id") or (items[-1].get("id") if items else None)
                    parameter = "after"
                else: break
                if not cursor or cursor in seen: raise Failure("DISCOVERY_UNAVAILABLE", "لم تكتمل صفحات دليل المزود.")
                seen.add(cursor)
                params = {parameter: cursor}
            else: raise Failure("DISCOVERY_UNAVAILABLE", "تجاوز دليل المزود حد الصفحات.")
            source = url
    unique = {item["id"]:item for item in result}
    if not unique: raise Failure("DISCOVERY_UNAVAILABLE", "لم يُرجع المزود نماذج مناسبة. راجع صلاحيات الحساب وعنوان API.")
    return {"models":sorted(unique.values(), key=lambda x:x["id"]), "source":source}
