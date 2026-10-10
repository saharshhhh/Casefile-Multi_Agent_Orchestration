import config


def cost_in_dollars(input_tokens, output_tokens):
    return (
        input_tokens * config.PRICE_PER_M_INPUT
        + output_tokens * config.PRICE_PER_M_OUTPUT
    ) / 1_000_000


def charge(state, result):
    """Record what a finished call actually cost."""
    state.llm_calls += 1
    state.tokens_used += result.input_tokens + result.output_tokens
    state.dollars_spent += cost_in_dollars(result.input_tokens, result.output_tokens)


def can_afford(state, prompt_text):
    """Before calling: would the worst case stay under the ceiling?"""
    est_input = len(prompt_text) // 4 + 1       # rough rule: 1 token is about 4 letters
    worst_tokens = est_input + config.MAX_OUTPUT_TOKENS
    worst_dollars = cost_in_dollars(est_input, config.MAX_OUTPUT_TOKENS)

    within_tokens = state.tokens_used + worst_tokens <= config.MAX_TOKENS
    within_dollars = state.dollars_spent + worst_dollars <= config.MAX_DOLLARS
    return within_tokens and within_dollars