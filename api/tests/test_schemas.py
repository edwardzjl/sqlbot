import unittest

from langchain.schema import AgentAction

from sqlbot.schemas import (
    ChatMessage,
    Conversation,
    IntermediateStep,
    IntermediateSteps,
)


class TestIntermediateStep(unittest.TestCase):
    def test_obj_to_step(self):
        _obj = (
            AgentAction(tool="some_tool", tool_input="some_input", log="some log"),
            "baz",
        )
        step = IntermediateStep.model_validate(_obj)
        action = step[0]
        self.assertDictEqual(
            action,
            {
                "type": "AgentAction",
                "tool": "some_tool",
                "tool_input": "some_input",
                "log": "some log",
            },
        )
        observation = step[1]
        self.assertEqual(observation, "baz")

    def test_step_to_obj(self):
        step = IntermediateStep(
            root=[
                AgentAction(tool="some_tool", tool_input="some_input", log="some log"),
                "baz",
            ]
        )
        self.assertListEqual(
            step.model_dump(),
            [
                {
                    "type": "AgentAction",
                    "tool": "some_tool",
                    "tool_input": "some_input",
                    "log": "some log",
                },
                "baz",
            ],
        )

    def test_str_to_step(self):
        step_str = (
            '[{"tool":"some_tool","tool_input":"some_input","log":"some log"},"baz"]'
        )
        step = IntermediateStep.model_validate_json(step_str)
        action = step[0]
        self.assertDictEqual(
            action,
            {
                "tool": "some_tool",
                "tool_input": "some_input",
                "log": "some log",
            },
        )
        observation = step[1]
        self.assertEqual(observation, "baz")

    def test_step_to_str(self):
        step = IntermediateStep(
            root=[
                AgentAction(tool="some_tool", tool_input="some_input", log="some log"),
                "baz",
            ]
        )
        self.assertEqual(
            step.model_dump_json(),
            '[{"tool":"some_tool","tool_input":"some_input","log":"some log","type":"AgentAction"},"baz"]',
        )


class TestIntermediateSteps(unittest.TestCase):
    def test_obj_to_steps(self):
        _obj = [
            (
                AgentAction(tool="some_tool", tool_input="some_input", log="some log"),
                "baz",
            )
        ]
        steps = IntermediateSteps.model_validate(_obj)
        self.assertEqual(len(steps), 1)
        step = steps[0]  # IntermediateStep
        self.assertDictEqual(
            step[0],
            {
                "type": "AgentAction",
                "tool": "some_tool",
                "tool_input": "some_input",
                "log": "some log",
            },
        )
        self.assertEqual(step[1], "baz")

    def test_str_to_steps(self):
        _str = (
            '[[{"tool":"some_tool","tool_input":"some_input","log":"some log"},"baz"]]'
        )
        steps = IntermediateSteps.model_validate_json(_str)
        self.assertEqual(len(steps), 1)
        step = steps[0]  # IntermediateStep
        self.assertDictEqual(
            step[0],
            {
                "tool": "some_tool",
                "tool_input": "some_input",
                "log": "some log",
            },
        )
        self.assertEqual(step[1], "baz")

    def test_steps_to_obj(self):
        steps = IntermediateSteps(
            root=[
                [
                    AgentAction(
                        tool="some_tool", tool_input="some_input", log="some log"
                    ),
                    "baz",
                ]
            ]
        )
        self.assertListEqual(
            steps.model_dump(),
            [
                [
                    {
                        "type": "AgentAction",
                        "tool": "some_tool",
                        "tool_input": "some_input",
                        "log": "some log",
                    },
                    "baz",
                ]
            ],
        )

    def test_steps_to_str(self):
        steps = IntermediateSteps(
            root=[
                [
                    AgentAction(
                        tool="some_tool", tool_input="some_input", log="some log"
                    ),
                    "baz",
                ]
            ]
        )
        self.assertEqual(
            steps.model_dump_json(),
            '[[{"tool":"some_tool","tool_input":"some_input","log":"some log","type":"AgentAction"},"baz"]]',
        )


class TestConversationSchema(unittest.TestCase):
    def test_create_conversation(self):
        conv = Conversation(title=f"foo", owner="bar")
        self.assertIsNotNone(conv.created_at)
        self.assertIsNotNone(conv.updated_at)
        # created_at and updated_at are not equal in unittests in github actions.
        # self.assertEqual(conv.created_at, conv.updated_at)


class TestMessageSchema(unittest.TestCase):
    def test_create_message(self):
        msg = ChatMessage(from_="ai", content="foo", type="stream")


if __name__ == "__main__":
    unittest.main()
