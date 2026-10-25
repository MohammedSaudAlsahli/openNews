"""Exercise real provider SDK parsing locally; no credentials or remote requests."""
import asyncio
import httpx
from agno.models.message import Message
from agno.models.openai import OpenAIChat, OpenAIResponses
from openai import AsyncOpenAI


def test_openai_adapters_parse_sdk_responses_with_local_transport():
    async def scenario():
        seen = []
        def respond(request):
            seen.append(request.url.path)
            if request.url.path.endswith('/chat/completions'):
                result = {'id': 'chat-fixture', 'object': 'chat.completion', 'created': 1, 'model': 'fixture', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Local chat'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 1, 'completion_tokens': 2, 'total_tokens': 3}}
            else:
                result = {'id': 'resp_fixture', 'object': 'response', 'created_at': 1, 'model': 'fixture', 'status': 'completed', 'output': [{'id': 'msg_fixture', 'type': 'message', 'role': 'assistant', 'status': 'completed', 'content': [{'type': 'output_text', 'text': 'Local response', 'annotations': []}]}], 'usage': {'input_tokens': 1, 'output_tokens': 2, 'total_tokens': 3}}
            return httpx.Response(200, json=result)
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False) as transport:
            client = AsyncOpenAI(api_key='fixture-not-a-key', base_url='https://fixture.invalid/v1', http_client=transport, max_retries=0)
            for model, expected in [(OpenAIChat(id='fixture', async_client=client), 'Local chat'), (OpenAIResponses(id='fixture', async_client=client), 'Local response')]:
                result = await model.ainvoke([Message(role='user', content='Local request')], Message(role='assistant'))
                assert result.content == expected
        assert seen == ['/v1/chat/completions', '/v1/responses']
    asyncio.run(scenario())


def test_litellm_real_mock_completion_and_stream(monkeypatch):
    monkeypatch.setenv('LITELLM_LOCAL_MODEL_COST_MAP', 'True')
    from agno.models.litellm import LiteLLM
    async def scenario():
        model = LiteLLM(id='openai/fixture', api_key='fixture-not-a-key', request_params={'mock_response': 'Local summary'})
        messages = [Message(role='user', content='Local request')]
        result = await model.ainvoke(messages, Message(role='assistant'))
        assert result.content == 'Local summary'
        chunks = [chunk.content or '' async for chunk in model.ainvoke_stream(messages, Message(role='assistant'))]
        assert ''.join(chunks) == 'Local summary'
    asyncio.run(scenario())
