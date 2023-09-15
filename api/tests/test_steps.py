import unittest

from langchain.schema import AgentAction

from sqlbot.steps import IntermediateSteps, IntermediateStepsStore


class TestStepSchema(unittest.TestCase):
    def test_create_conversation(self):
        steps = [
            (
                AgentAction(tool="some_tool", tool_input="some input", log="some log"),
                "foo",
            ),
            (
                AgentAction(
                    tool="some_other_tool",
                    tool_input="some other input",
                    log="some other log",
                ),
                "bar",
            ),
        ]
        intermediate_steps = IntermediateSteps(__root__=steps)
        ser = intermediate_steps.json()
        print(ser)
        deser = IntermediateSteps.parse_raw(ser)
        self.assertEqual(intermediate_steps, deser)


if __name__ == "__main__":
    unittest.main()
