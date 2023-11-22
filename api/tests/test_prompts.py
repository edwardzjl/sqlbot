import unittest

from langchain.schema import AIMessage, HumanMessage, SystemMessage

from sqlbot.prompts import ChatMLPromptValue


class TestChatMLPromptValue(unittest.TestCase):
    def test_format_system_message(self):
        prompt_value = ChatMLPromptValue(messages=[SystemMessage(content="foo")])
        expected = """<|im_start|>system
foo<|im_end|>
<|im_start|>assistant
"""
        self.assertEqual(prompt_value.to_string(), expected)

    def test_format_user_message(self):
        prompt_value = ChatMLPromptValue(messages=[HumanMessage(content="foo")])
        expected = """<|im_start|>user
foo<|im_end|>
<|im_start|>assistant
"""
        self.assertEqual(prompt_value.to_string(), expected)

    def test_format_assistant_message(self):
        prompt_value = ChatMLPromptValue(messages=[AIMessage(content="foo")])
        expected = """<|im_start|>assistant
foo<|im_end|>
<|im_start|>assistant
"""
        self.assertEqual(prompt_value.to_string(), expected)


if __name__ == "__main__":
    unittest.main()
