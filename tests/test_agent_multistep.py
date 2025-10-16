"""Integration-style tests for multi-step planning in the local agent."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest import IsolatedAsyncioTestCase

from local_agent import LocalContentAgent


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
        agent = LocalContentAgent()

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

        async def fake_get_available_tools(_: str | None = None) -> list[dict[str, Any]]:
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

    async def test_agent_retries_after_connection_error(self) -> None:
        agent = LocalContentAgent()

        tool_invocations: list[tuple[str, dict[str, Any]]] = []

        async def fake_call_mcp_tool(name: str, arguments: dict[str, Any]) -> str:
            tool_invocations.append((name, arguments))
            return "Fetched page content" if name == "fetch_web_content" else "Blog prompt instructions"

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

        async def fake_get_available_tools(_: str | None = None) -> list[dict[str, Any]]:
            return tool_definitions

        agent.get_available_tools_for_function_calling = fake_get_available_tools  # type: ignore[assignment]

        first_call_response = _FakeResponse(
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
        )

        second_call_response = _FakeResponse(
            choices=[
                _FakeChoice(
                    message=_FakeMessage(
                        content="Here is your blog post.",
                        tool_calls=None,
                    )
                )
            ]
        )

        responses = [first_call_response, second_call_response]

        class _FlakyCompletions:
            def __init__(self) -> None:
                self.calls = 0

            async def create(self, **_: Any) -> _FakeResponse:
                self.calls += 1
                if self.calls == 2:
                    raise Exception("Connection error")
                if not responses:
                    raise AssertionError("No responses left for fake completions")
                return responses.pop(0)

        class _FakeChat:
            def __init__(self) -> None:
                self.completions = _FlakyCompletions()

        class _FakeClient:
            def __init__(self) -> None:
                self.chat = _FakeChat()

        agent.client = _FakeClient()  # type: ignore[assignment]

        result = await agent.process_message(
            "fetch the web page and make a blog post from it: https://developer.nvidia.com/buy-jetson"
        )

        self.assertEqual(result, "Here is your blog post.")
        self.assertEqual(
            tool_invocations,
            [
                (
                    "fetch_web_content",
                    {"url": "https://developer.nvidia.com/buy-jetson"},
                )
            ],
        )

    async def test_connection_error_surfaces_actionable_hint(self) -> None:
        agent = LocalContentAgent()

        async def fake_get_available_tools(_: str | None = None) -> list[dict[str, Any]]:
            return []

        agent.get_available_tools_for_function_calling = fake_get_available_tools  # type: ignore[assignment]

        class _AlwaysFailCompletions:
            def __init__(self) -> None:
                self.calls = 0

            async def create(self, **_: Any) -> _FakeResponse:
                self.calls += 1
                raise Exception("Connection error")

        class _AlwaysFailChat:
            def __init__(self) -> None:
                self.completions = _AlwaysFailCompletions()

        class _AlwaysFailClient:
            def __init__(self) -> None:
                self.chat = _AlwaysFailChat()

        agent.client = _AlwaysFailClient()  # type: ignore[assignment]

        result = await agent.process_message("Write something without tools")

        self.assertTrue(result.startswith("Error: Unable to reach the LLM endpoint"))
        self.assertIn("Ensure a local LLM server is running", result)

    async def test_missing_choices_returns_useful_error(self) -> None:
        agent = LocalContentAgent()

        async def fake_get_available_tools(_: str | None = None) -> list[dict[str, Any]]:
            return []

        agent.get_available_tools_for_function_calling = fake_get_available_tools  # type: ignore[assignment]

        class _NoChoiceResponse:
            def __init__(self) -> None:
                self.choices: list[Any] | None = None

        class _NoChoiceCompletions:
            async def create(self, **_: Any) -> _NoChoiceResponse:
                return _NoChoiceResponse()

        class _NoChoiceChat:
            def __init__(self) -> None:
                self.completions = _NoChoiceCompletions()

        class _NoChoiceClient:
            def __init__(self) -> None:
                self.chat = _NoChoiceChat()

        agent.client = _NoChoiceClient()  # type: ignore[assignment]

        result = await agent.process_message("write something")

        self.assertTrue(result.startswith("Error: LLM returned no choices."))
