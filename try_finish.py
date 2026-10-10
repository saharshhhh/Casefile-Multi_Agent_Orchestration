from llm.client import LLMClient

r = LLMClient().ask("Reply with one word.", "Say hi")
print(repr(r.finish_reason), r.output_tokens)