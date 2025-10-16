"""Integration-style tests for multi-step planning in the local agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest import IsolatedAsyncioTestCase

from local_agent import LocalYouTubeAgent


@dataclass
class _FakeFunction:
    name: str
    arguments: str


@dataclass
class _FakeToolCall:
    id: str
    function: _FakeFunction


@dataclass
class _FakeMessage:
    content: str
    tool_calls: list[_FakeToolCall] | None = None


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeResponse:
    choices: list[_FakeChoice]


class MultiStepPlanningTests(IsolatedAsyncioTestCase):
    async def test_agent_executes_two_stage_plan(self) -> None:
        agent = LocalYouTubeAgent()

        tool_invocations: list[tuple[str, dict[str, Any]]] = []

        async def fake_call_mcp_tool(name: str, arguments: dict[str, Any]) -> str:
            tool_invocations.append((name, arguments))
            if name == "fetch_web_content":
                return "Fetched page content"
            if name == "fetch_instructions":
                return "Blog prompt instructions"
            return "Unknown tool"

        agent.call_mcp_tool = fake_call_mcp_tool  # type: ignore[assignment]

        tool_definitions = [
            {
                "type": "function",
                "function": {
                    "name": "fetch_web_content",
                    "description": "fetch web",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_instructions",
                    "description": "instructions",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
        ]

        async def fake_get_available_tools() -> list[dict[str, Any]]:
            return tool_definitions

        agent.get_available_tools_for_function_calling = fake_get_available_tools  # type: ignore[assignment]

        responses = [
            _FakeResponse(
                choices=[
                    _FakeChoice(
                        message=_FakeMessage(
                            content="",
                            tool_calls=[
                                _FakeToolCall(
                                    id="call-1",
                                    function=_FakeFunction(
                                        name="fetch_web_content",
                                        arguments=json.dumps(
                                            {"url": "https://developer.nvidia.com/buy-jetson"}
                                        ),
                                    ),
                                )
                            ],
                        )
                    )
                ]
            ),
            _FakeResponse(
                choices=[
                    _FakeChoice(
                        message=_FakeMessage(
                            content="",
                            tool_calls=[
                                _FakeToolCall(
                                    id="call-2",
                                    function=_FakeFunction(
                                        name="fetch_instructions",
                                        arguments=json.dumps({"prompt_name": "write_blog_post"}),
                                    ),
                                )
                            ],
                        )
                    )
                ]
            ),
            _FakeResponse(
                choices=[
                    _FakeChoice(
                        message=_FakeMessage(
                            content="Here is your blog post.",
                            tool_calls=None,
                        )
                    )
                ]
            ),
        ]

        class _FakeCompletions:
            async def create(self, **_: Any) -> _FakeResponse:
                if not responses:
                    raise AssertionError("No responses left for fake completions")
                return responses.pop(0)

        class _FakeChat:
            def __init__(self) -> None:
                self.completions = _FakeCompletions()

        class _FakeClient:
            def __init__(self) -> None:
                self.chat = _FakeChat()

        agent.client = _FakeClient()  # type: ignore[assignment]

        user_prompt = (
            "fetch the web page and make a blog post from it: "
            "https://developer.nvidia.com/buy-jetson"
        )

        result = await agent.process_message(user_prompt)

        self.assertEqual(result, "Here is your blog post.")
        self.assertEqual(
            tool_invocations,
            [
                (
                    "fetch_web_content",
                    {"url": "https://developer.nvidia.com/buy-jetson"},
                ),
                (
                    "fetch_instructions",
                    {"prompt_name": "write_blog_post"},
                ),
            ],
        )
        self.assertEqual(agent.conversation_history[-1]["content"], result)
        self.assertEqual(agent.conversation_history[-1]["role"], "assistant")
