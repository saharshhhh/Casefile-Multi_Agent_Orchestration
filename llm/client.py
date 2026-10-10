import time
from dataclasses import dataclass
import cohere
from cohere.core.api_error import ApiError
import config


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    finish_reason: str = ""      # why the model stopped writing


class LLMClient:
    def __init__(self):
        # Reads the key from the CO_API_KEY setting automatically
        self.client = cohere.ClientV2()

    def ask(self, system, user):
        for attempt in range(4):
            try:
                response = self.client.chat(
                    model=config.MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0,
                    max_tokens=config.MAX_OUTPUT_TOKENS,
                )
                break
            except ApiError as error:
                if error.status_code == 429 and attempt < 3:
                    time.sleep(20 * (attempt + 1))     # wait longer each time
                    continue
                raise

        # Keep only the text parts of the reply
        text = "".join(
            part.text for part in response.message.content if part.type == "text"
        )

        return LLMResult(
            text=text,
            input_tokens=int(response.usage.tokens.input_tokens),
            output_tokens=int(response.usage.tokens.output_tokens),
            finish_reason=str(response.finish_reason),
        )