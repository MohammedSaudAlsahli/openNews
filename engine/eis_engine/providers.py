"""Agno adapters and owner-only local credentials. Never include secrets in diagnostics."""
import importlib
import importlib.metadata
import inspect
import json
import os
import stat
from pathlib import Path
from uuid import UUID
from urllib.parse import urlsplit
from .contracts import Failure

CONFIG_FIELDS = {"base_url", "azure_endpoint", "azure_deployment", "api_version", "region",
                 "region_name", "aws_region", "project_id", "location", "host", "account_id", "gateway_id",
                 "resource", "url", "base_host_url", "api_base", "vertexai"}
LOCAL = {"ollama", "ollama-responses", "lmstudio", "llmman", "llama-cpp", "vllm", "nexus", "litellm-openai"}
CREDENTIAL_FIELDS = {"api_key", "aws_access_key_id", "aws_secret_access_key", "aws_session_token",
                     "auth_token", "portkey_api_key", "virtual_key", "service_account_info", "azure_management_token"}


def keychain_read(account):
    """Legacy symbol retained for callers; runtime no longer reads Keychain."""
    raise Failure("AUTH_REQUIRED", "أعد حفظ بيانات المزود في الإعدادات المحلية.")


def ollama_cloud(config):
    endpoint = config.get("host") or config.get("base_url") or ""
    parsed = urlsplit(endpoint)
    if parsed.hostname == "ollama.com":
        if parsed.scheme != "https" or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path.rstrip("/") not in ("", "/v1"):
            raise Failure("VALIDATION_ERROR", "استخدم https://ollama.com لاتصال Ollama Cloud.")
        return True
    return False


def read_credentials(profile):
    name = profile.get("credential_path")
    if not name:
        return {}
    if profile.get("provider_key") in LOCAL and not Path(name).exists():
        return {}
    try:
        path = Path(name)
        UUID(path.stem)
        if path.suffix != ".json" or path.parent.name != ".providers" or not path.is_absolute():
            raise ValueError()
        # Reject symlinks in every component, and enforce the private directory/file modes.
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError()
        parent = path.parent.stat()
        if stat.S_IMODE(parent.st_mode) != 0o700 or parent.st_uid != os.getuid():
            raise ValueError()
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "r") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 65536:
                raise ValueError()
            values = json.load(stream)
        if not isinstance(values, dict) or set(values) - CREDENTIAL_FIELDS:
            raise ValueError()
        if any(not isinstance(v, (str, dict)) or (isinstance(v, dict) and k != "service_account_info") for k, v in values.items()):
            raise ValueError()
        return values
    except (OSError, ValueError, TypeError):
        raise Failure("AUTH_REQUIRED", "تعذّر قراءة بيانات المزود المحلية بأمان. أعد حفظها من الإعدادات.") from None


def adapter_class(entry):
    return getattr(importlib.import_module(entry["module"]), entry["class_name"])


def build_catalog():
    from agno.models.utils import MODEL_PROVIDER_CLASSES
    entries = []
    for key, (module, classname) in sorted(MODEL_PROVIDER_CLASSES.items()):
        row = dict(id=key, name=classname, module=module, class_name=classname,
                   status="needs_dependency", fields=[], default_model="", credential="api_key",
                   credential_fields=["api_key"], note="", live_validated=False)
        try:
            cls = getattr(importlib.import_module(module), classname)
            params = inspect.signature(cls).parameters
            default = params.get("id")
            model_id = default.default if default else ""
            row.update(default_model=model_id if isinstance(model_id, str) else "",
                       fields=sorted(CONFIG_FIELDS & params.keys()), status="ready")
            if key.startswith("azure-") and key != "azure-foundry-claude":
                row["fields"] += ["subscription_id", "resource_group", "account_name"]
                row["credential_fields"] += ["azure_management_token"]
            row["default_base_url"] = next((params[x].default for x in ("base_url", "host", "api_base") if x in params and isinstance(params[x].default, str)), "")
            if key in LOCAL:
                row["credential"] = "local_server"
            elif key.startswith("aws-"):
                row.update(credential="cloud_configuration", credential_fields=["aws_access_key_id", "aws_secret_access_key", "aws_session_token"])
            elif key == "vertexai-claude":
                row.update(credential="cloud_configuration", credential_fields=["service_account_info"])
            elif key == "portkey":
                row["credential_fields"] = ["portkey_api_key", "virtual_key"]
            elif key == "google":
                row["credential_fields"] = ["api_key", "service_account_info"]
            if key.startswith(("aws-", "azure-", "vertexai-")) or key in {"ibm", "cloudflare", "langdb"}:
                row["note"] = "المهايئ متاح؛ يتطلب بيانات الحساب والمنطقة أو المشروع قبل الاتصال."
        except ImportError:
            row["note"] = "اعتماد المزود غير مثبت في هذه الحزمة."
        except Exception as error:
            row.update(status="adapter_error", note=type(error).__name__)
        entries.append(row)
    from .chatgpt_auth import ENTRY
    entries.append(dict(ENTRY))
    from .google_auth import ENTRY as GOOGLE_ENTRY
    entries.append(dict(GOOGLE_ENTRY))
    return {"agno_version": importlib.metadata.version("agno"), "providers": entries}


def catalog():
    return json.loads(Path(__file__).with_name("provider_catalog.json").read_text())


def google_credentials(values):
    from google.oauth2.service_account import Credentials
    info = values.get("service_account_info")
    if isinstance(info, str):
        info = json.loads(info)
    if not isinstance(info, dict):
        raise Failure("AUTH_REQUIRED", "أضف بيانات حساب خدمة Google من الإعدادات.")
    # Prevent a supplied credential file from redirecting its token request elsewhere.
    if info.get("token_uri") != "https://oauth2.googleapis.com/token":
        raise Failure("AUTH_REQUIRED", "عنوان اعتماد Google غير صالح.")
    return Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/cloud-platform"])


class ModelFactory:
    supports_tools = True
    supports_session_events = True
    def create(self, profile):
        entry = next((p for p in catalog()["providers"] if p["id"] == profile["provider_key"]), None)
        if not entry or entry["status"] != "ready":
            raise Failure("MODEL_UNSUPPORTED", "هذا المهايئ غير جاهز في الحزمة الحالية؛ راجع حالته في الإعدادات.")
        config = json.loads(profile["config_json"])
        if set(config) - set(entry["fields"]):
            raise Failure("VALIDATION_ERROR", "حقول إعداد غير مسموحة.")
        try:
            cls = adapter_class(entry)
            params = inspect.signature(cls).parameters
            values = read_credentials(profile)
            provider_key = profile["provider_key"]
            if provider_key.startswith("aws-") and not (values.get("aws_access_key_id") and values.get("aws_secret_access_key")):
                raise Failure("AUTH_REQUIRED", "أضف مفتاح AWS ومعرّف الوصول في الإعدادات.")
            if (provider_key == "vertexai-claude" or (provider_key == "google" and str(config.get("vertexai", "")).lower() == "true")) and not values.get("service_account_info"):
                raise Failure("AUTH_REQUIRED", "أضف بيانات حساب خدمة Google في الإعدادات.")
            options = {"id": profile["model_id"], **{k:v for k,v in config.items() if k in params}}
            if provider_key in {"ollama", "ollama-responses"}:
                cloud = ollama_cloud(config)
                if cloud and not values.get("api_key"):
                    raise Failure("AUTH_REQUIRED", "أضف مفتاح Ollama Cloud في الإعدادات أولًا.")
                # Do not let Agno's OLLAMA_API_KEY/OLLAMA_HOST environment defaults
                # silently move a local profile to a remote service.
                options["host"] = "https://ollama.com" if cloud else (config.get("host") or config.get("base_url") or "http://127.0.0.1:11434")
                options["api_key"] = values.get("api_key") or None

            if "vertexai" in options:
                options["vertexai"] = str(options["vertexai"]).lower() == "true"
            for key, value in values.items():
                if key in params and key != "service_account_info" and value:
                    options[key] = value
            if profile["provider_key"] == "aws-claude":
                for source, dest in [("aws_access_key_id", "aws_access_key"), ("aws_secret_access_key", "aws_secret_key")]:
                    if values.get(source): options[dest] = values[source]
            if values.get("service_account_info"):
                credential = google_credentials(values)
                if "credentials" in params:
                    options["credentials"] = credential
                    options["vertexai"] = True
                elif profile["provider_key"] == "vertexai-claude":
                    from anthropic import AnthropicVertex, AsyncAnthropicVertex
                    arguments = {"project_id": config.get("project_id"), "region": config.get("region"), "credentials": credential}
                    options["client"] = AnthropicVertex(**arguments)
                    options["async_client"] = AsyncAnthropicVertex(**arguments)
            if entry["credential"] == "api_key" and not any(values.get(x) for x in entry.get("credential_fields", ["api_key"])):
                raise Failure("AUTH_REQUIRED", "أضف مفتاح المزود في الإعدادات أولًا.")
            for key, value in {"timeout":90.0, "max_retries":0, "retry_with_guidance":False, "store":False, "max_output_tokens":8192}.items():
                if key in params: options[key] = value
            return cls(**options)
        except Failure:
            raise
        except Exception:
            raise Failure("MODEL_UNSUPPORTED", "تعذّرت تهيئة المهايئ. راجع بيانات الحساب وإعدادات المزود.") from None

    async def run_stream(self, profile, instructions, data, schema, on_delta, tools=None, on_turn=None, on_reasoning=None, session_id=None, user_id=None, run_id=None):
        return await self.run(profile,instructions,data,schema,on_delta=on_delta, tools=tools, on_turn=on_turn, on_reasoning=on_reasoning, session_id=session_id, user_id=user_id, run_id=run_id)

    async def run(self, profile, instructions, data, schema, on_delta=None, tools=None, on_turn=None, on_reasoning=None, session_id=None, user_id=None, run_id=None):
        from agno.agent import Agent
        if profile["provider_key"] == "openai-chatgpt":
            from .chatgpt_auth import ChatGPTResponses, access_token
            model = ChatGPTResponses(id=profile["model_id"], api_key=await access_token(profile), base_url="https://api.openai.com/v1", store=False, retries=0, max_retries=0, timeout=90)
        elif profile["provider_key"] == "google-oauth":
            from .google_auth import access_token as google_token
            from google.oauth2.credentials import Credentials
            from agno.models.google import Gemini
            config = json.loads(profile["config_json"])
            model = Gemini(id=profile["model_id"], vertexai=True, project_id=config["project_id"],
                location=config.get("location","us-central1"), credentials=Credentials(await google_token(profile)),
                retries=0, timeout=90, max_output_tokens=8192)
        else:
            model = self.create(profile)
        if profile.get("_activity_translation") and profile["provider_key"] in {"openai", "openai-chatgpt"}:
            if profile["model_id"].startswith(("gpt-5", "gpt-6", "o3", "o4")) and hasattr(model, "reasoning_effort"):
                model.reasoning_effort = "low"
        # Request public summaries only on known OpenAI reasoning model families.
        # Other providers keep their configured behavior; never fabricate a trace.
        if on_reasoning and profile["provider_key"] in {"openai", "openai-chatgpt"} and hasattr(model, "reasoning_summary"):
            if profile["model_id"].startswith(("gpt-5", "gpt-6", "o3", "o4")):
                model.reasoning_summary = "auto"
        if profile["provider_key"] == "openai-chatgpt":
            model.on_reasoning_delta = on_reasoning
            model.on_text_delta = on_delta
            model.on_response_start = on_turn
        agent = Agent(model=model, instructions=instructions, session_id=session_id, user_id=user_id,
                      add_history_to_context=False,
                      output_schema=schema, structured_outputs=False,
                      tools=tools or [], tool_call_limit=10, search_knowledge=False, telemetry=False,
                      retries=0, debug_mode=False, parse_response=on_delta is None)
        try:
            if on_delta and profile["provider_key"] != "openai-chatgpt":
                from agno.run.agent import RunOutput, RunContentEvent, RunErrorEvent, ReasoningContentDeltaEvent
                response = None
                provider_errors = []
                original_stream = model.ainvoke_stream
                async def observed_stream(*args, **kwargs):
                    if on_turn: on_turn()
                    try:
                        async for chunk in original_stream(*args, **kwargs): yield chunk
                    except Exception as error:
                        provider_errors.append(error)
                        raise
                model.ainvoke_stream = observed_stream
                stream = agent.arun(json.dumps(data,ensure_ascii=False),stream=True,stream_events=True,yield_run_output=True, run_id=run_id)
                try:
                    async for event in stream:
                        if isinstance(event,RunContentEvent) and isinstance(event.content,str): on_delta(event.content)
                        elif isinstance(event,ReasoningContentDeltaEvent) and on_reasoning: on_reasoning(event.reasoning_content)
                        elif isinstance(event,RunOutput): response = event
                        elif isinstance(event,RunErrorEvent):
                            if provider_errors: raise provider_errors[-1]
                            raise Failure("MODEL_RESPONSE_INVALID","لم يكتمل رد النموذج. حاول مجددًا.")
                finally:
                    await stream.aclose()
                    model.ainvoke_stream = original_stream
                if response is None: raise Failure("MODEL_RESPONSE_INVALID","لم يكتمل رد النموذج. حاول مجددًا.")
            else:
                response = await agent.arun(json.dumps(data, ensure_ascii=False), run_id=run_id)
            if isinstance(response.content, schema):
                return response.content
            if isinstance(response.content, str):
                return schema.model_validate_json(response.content)
            return schema.model_validate(response.content)
        except Failure:
            raise
        except Exception as error:
            from pydantic import ValidationError
            if isinstance(error, ValidationError):
                raise Failure("MODEL_RESPONSE_INVALID", "وصل رد بتنسيق غير صالح. أعد المحاولة؛ لا يعني هذا تسجيل خروجك.") from None
            status = getattr(error, "status_code", None)
            from openai import APIConnectionError, APITimeoutError
            import httpx
            if isinstance(error, (httpx.TransportError, APIConnectionError, APITimeoutError, TimeoutError)):
                raise Failure("NETWORK_ERROR", "تعذّر الوصول إلى المزوّد. بيانات دخولك محفوظة؛ تحقق من الشبكة وحاول مجددًا.") from None
            if isinstance(status, int) and status >= 500:
                raise Failure("PROVIDER_UNAVAILABLE", "الخدمة غير متاحة مؤقتًا. بيانات دخولك محفوظة؛ حاول لاحقًا.") from None
            code = {401: "AUTH_REQUIRED", 403: "PERMISSION_DENIED", 429: "RATE_LIMITED"}.get(status, "MODEL_UNSUPPORTED")
            # Never return provider exception text: it can contain prompts, headers, or secrets.
            raise Failure(code, "تعذّر إكمال طلب النموذج أو التحقق من بنيته. راجع المفتاح والنموذج والاتصال.") from None
