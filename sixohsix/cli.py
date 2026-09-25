import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from sixohsix.cases import REPO, load_cases


def cmd_eval(args) -> None:
    from sixohsix import evaluate

    cases = load_cases()
    runners = ["baseline", "agent"] if args.runner == "all" else [args.runner]
    for runner in runners:
        if runner == "agent" and not evaluate.has_key():
            print("ANTHROPIC_API_KEY not set; skipping the agent runner.")
            continue
        for r in evaluate.run(runner, cases, only=args.case):
            s = r.scores
            print(
                f"{runner:8} {r.case_id:32} overall {s.overall:.2f}  f1 {s.obligation_f1:.2f}  timing {s.timing_accuracy:.2f}"
                f"  consid {s.consideration_correct:.2f}  grounding {s.grounding:.2f}"
                + (f"  tokens {r.input_tokens}/{r.output_tokens}  {r.seconds}s" if runner == "agent" else "")
            )


def cmd_serve(args) -> None:
    import uvicorn

    uvicorn.run("sixohsix.server:app", host="127.0.0.1", port=args.port)


def cmd_memo(args) -> None:
    from sixohsix import evaluate, memo

    case = next((c for c, _ in load_cases() if c.id == args.case_id), None)
    result = next((r for r in evaluate.load_results(args.runner) if r.case_id == args.case_id), None)
    if case is None or result is None:
        sys.exit(f"No {args.runner} result for {args.case_id}. Run `six-oh-six eval` first.")
    out = Path(args.o or f"{args.case_id}-{args.runner}.docx")
    out.write_bytes(memo.render(case, result.analysis))
    print(out)


def main() -> None:
    load_dotenv(REPO / ".env")
    p = argparse.ArgumentParser(prog="six-oh-six")
    sub = p.add_subparsers(required=True)

    e = sub.add_parser("eval", help="run runners over the cases and write results")
    e.add_argument("--runner", choices=["baseline", "agent", "all"], default="all")
    e.add_argument("--case", help="run one case id")
    e.set_defaults(fn=cmd_eval)

    s = sub.add_parser("serve", help="start the web UI")
    s.add_argument("--port", type=int, default=8606)
    s.set_defaults(fn=cmd_serve)

    m = sub.add_parser("memo", help="write a .docx memo from a stored result")
    m.add_argument("case_id")
    m.add_argument("--runner", choices=["baseline", "agent"], default="agent")
    m.add_argument("-o", help="output path")
    m.set_defaults(fn=cmd_memo)

    args = p.parse_args()
    args.fn(args)
