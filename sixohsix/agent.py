"""The technical accountant: a tool-use loop over one contract that ends in a validated Analysis."""

import os
import time

import anthropic
from pydantic import ValidationError

from sixohsix.guidance import GUIDANCE
from sixohsix.retrieval import search
from sixohsix.schema import KINDS, Analysis, Case, Step

MAX_TURNS = 14
TRACE_CHARS = 400


def model() -> str:
    return os.environ.get("SIXOHSIX_MODEL", "claude-sonnet-5")


SYSTEM = f"""You are a technical accountant preparing an ASC 606 revenue recognition analysis for the reporting entity (the seller) named in the request. Read the contract through your tools and work the five steps:

1. Identify the contract. Note anything that casts doubt on enforceability or collectability.
2. Identify the performance obligations. Decide which promises are distinct, which form a series, and which are not obligations at all (assurance warranties, customer breach remedies, administrative terms, incidental rights).
3. Determine the transaction price: fixed amounts, variable consideration, the constraint, and any sales- or usage-based royalty on a license of IP.
4. Allocate the price. Note where standalone selling prices are needed.
5. Decide when each obligation is satisfied: over time or at a point in time.

Classify every obligation as one of these kinds:
{chr(10).join(f"- {k.value}: {info.label}. Usually {info.usual_timing.value}." for k, info in KINDS.items())}

Usual timing is a starting point, not an answer. Read what the contract actually promises. A software license the customer runs itself is a different promise from hosted access, whatever the clause is called.

Rules:
- You start with only the clause index. Use search_contract to find clauses and read_clause to read one in full. Cite only clause ids you have read in full, and cite every clause a conclusion rests on.
- Use lookup_guidance before relying on a topic, and cite the ASC paragraph numbers it returns.
- When the contract does not settle a judgment call, add it to open_questions instead of guessing.
- Only the reporting entity's revenue matters. Ignore the customer's accounting.
- Finish by calling submit_analysis exactly once with your complete analysis. If it returns a validation error, fix the input and call it again."""

TOOLS = [
    {
        "name": "search_contract",
        "description": "Rank the contract's clauses against a keyword query (BM25). Returns up to 5 clause ids, headings and a short snippet each.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Keywords, e.g. 'royalty net sales report'."}},
            "required": ["query"],
        },
    },
    {
        "name": "read_clause",
        "description": "Return the full text of one clause by id.",
        "input_schema": {
            "type": "object",
            "properties": {"clause_id": {"type": "string", "description": "A clause id from the index, e.g. 'c-004'."}},
            "required": ["clause_id"],
        },
    },
    {
        "name": "lookup_guidance",
        "description": "Return the ASC 606 paragraph references and a plain-language summary for one topic.",
        "input_schema": {
            "type": "object",
            "properties": {"topic": {"type": "string", "enum": list(GUIDANCE)}},
            "required": ["topic"],
        },
    },
    {
        "name": "submit_analysis",
        "description": "Submit the final ASC 606 analysis. Every clause id cited must be one you read.",
        "input_schema": Analysis.model_json_schema(),
        "cache_control": {"type": "ephemeral"},
    },
]


def opening(case: Case) -> str:
    index = "\n".join(f"[{c.id}] {c.heading}" for c in case.clauses)
    return (
        f"Reporting entity (seller): {case.reporting_entity}\nCustomer: {case.customer}\n"
        f"Contract: {case.title} ({case.contract_type})\n\nClause index:\n{index}"
    )


def run_tool(case: Case, name: str, args: dict) -> tuple[str, bool]:
    """Returns (output, is_error)."""
    clauses = {c.id: c for c in case.clauses}
    match name:
        case "search_contract":
            hits = search(case.clauses, args.get("query", ""))
            if not hits:
                return "No clauses matched. Try other keywords.", False
            return "\n".join(f"[{c.id}] {c.heading}: {c.text[:160]}..." for c in hits), False
        case "read_clause":
            c = clauses.get(args.get("clause_id", ""))
            if c is None:
                return f"No clause with id {args.get('clause_id')!r}. Ids run {case.clauses[0].id} to {case.clauses[-1].id}.", True
            return f"[{c.id}] {c.heading}\n{c.text}", False
        case "lookup_guidance":
            note = GUIDANCE.get(args.get("topic", ""))
            if note is None:
                return f"Unknown topic. Choose one of: {', '.join(GUIDANCE)}.", True
            return f"ASC {', '.join(note.refs)}\n{note.paraphrase}", False
    return f"Unknown tool {name}.", True


class AgentError(RuntimeError):
    pass


def analyze(case: Case, max_turns: int = MAX_TURNS) -> tuple[Analysis, list[Step], dict[str, int], float]:
    client = anthropic.Anthropic()
    start = time.monotonic()
    messages: list[dict] = [{"role": "user", "content": opening(case)}]
    trace: list[Step] = []
    usage = dict(input_tokens=0, output_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=0)

    for turn in range(max_turns):
        # Forced tool choice can't be combined with thinking, so the last turn turns it off.
        final = {"tool_choice": {"type": "tool", "name": "submit_analysis"}, "thinking": {"type": "disabled"}}
        resp = client.messages.create(
            model=model(),
            max_tokens=16000,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages,
            **(final if turn == max_turns - 1 else {}),
        )
        for k in usage:
            usage[k] += getattr(resp.usage, k, 0) or 0
        messages.append({"role": "assistant", "content": resp.content})

        calls = [b for b in resp.content if b.type == "tool_use"]
        if not calls:
            messages.append({"role": "user", "content": "Call submit_analysis with your complete analysis."})
            continue

        results, analysis = [], None
        for call in calls:
            if call.name == "submit_analysis":
                try:
                    analysis = Analysis.model_validate(call.input)
                    out, err = "Accepted.", False
                except ValidationError as e:
                    out, err = f"Validation failed, fix and resubmit:\n{e}", True
            else:
                out, err = run_tool(case, call.name, call.input)
            trace.append(Step(tool=call.name, input=call.input, output=out[:TRACE_CHARS]))
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": out, "is_error": err})
        if analysis:
            return analysis, trace, usage, time.monotonic() - start
        messages.append({"role": "user", "content": results})

    last = trace[-1].output if trace else "no tool calls"
    raise AgentError(f"{case.id}: no valid analysis after {max_turns} turns; last step: {last}")

