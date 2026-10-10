import json
from pathlib import Path
from pydantic import ValidationError
from agents.base import AgentError
from tools.contracts import LookupPolicyInput, PriorClaimsInput, BenchmarkInput

DATA = Path(__file__).parent.parent / "data"


def load(filename):
    with open(DATA / filename) as f:
        return json.load(f)


def lookup_policy(inputs):
    policies = load("policies.json")
    if inputs.policy_no not in policies:
        raise AgentError(f"policy {inputs.policy_no} not found")
    return policies[inputs.policy_no]


def get_prior_claims(inputs):
    claims = load("prior_claims.json")
    return [c for c in claims if c["policy_no"] == inputs.policy_no]


def get_repair_benchmark(inputs):
    benchmarks = load("repair_benchmarks.json")
    if inputs.vehicle not in benchmarks:
        raise AgentError(f"no benchmark for vehicle {inputs.vehicle}")
    return benchmarks[inputs.vehicle]


# The tool list: each name, its contract, and the function behind it
TOOLS = {
    "lookup_policy": (LookupPolicyInput, lookup_policy),
    "get_prior_claims": (PriorClaimsInput, get_prior_claims),
    "get_repair_benchmark": (BenchmarkInput, get_repair_benchmark),
}


def call_tool(name, arguments):
    """The only door to the tools. It checks the contract first."""
    if name not in TOOLS:
        raise AgentError(f"unknown tool: {name}")

    contract, function = TOOLS[name]
    try:
        inputs = contract(**arguments)
    except (ValidationError, TypeError) as error:
        raise AgentError(f"bad input for {name}: {error}")

    return function(inputs)