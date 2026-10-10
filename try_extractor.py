from agents.extractor import make_extractor
from llm.client import LLMClient
from schemas.state import ClaimState

text = """
Claim number: C-1042
Policy: P-5531
Date of loss: 3 September 2026
Rear bumper replacement: 850.00
Paint and labour: 420.50
Total estimate: 1270.50
"""

state = ClaimState(claim_id="C-1042", claim_text=text)
make_extractor(LLMClient())(state)

print(state.extracted)
print("tokens:", state.tokens_used, " dollars:", round(state.dollars_spent, 5))