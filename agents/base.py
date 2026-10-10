class AgentError(Exception):
    """Raised when an agent can't do its job safely."""


def check_complete(result):
    """A reply that was cut off is not a reply we can trust."""
    if "MAX_TOKENS" in result.finish_reason.upper():
        raise AgentError("reply was cut off at the token limit")