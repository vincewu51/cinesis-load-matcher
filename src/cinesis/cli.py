import argparse
import json
import logging
from pathlib import Path

from .extraction import ExtractionError, extract, read_profile
from .models import DriverProfile
from .ranking import rank_loads
from .report import write_outputs
from .workbook import read_inputs


def main():
    parser = argparse.ArgumentParser(
        description="Extract a driver profile with OpenAI and rank loads with explicit assumptions."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["extract", "rank", "solve"]:
        p = sub.add_parser(name)
        p.add_argument("--workbook", type=Path, default=Path("data/input.xlsx"))
        if name in {"extract", "solve"}:
            p.add_argument(
                "--model", help="OpenAI model; defaults to OPENAI_MODEL or gpt-6-astra"
            )
        if name == "extract":
            p.add_argument("--output", type=Path, default=Path("outputs/profile.json"))
        else:
            p.add_argument("--output-dir", type=Path, default=Path("outputs"))
            p.add_argument(
                "--assumed-capacity-lb",
                type=float,
                help="Explicit conditional scenario; never recorded as a driver fact",
            )
            p.add_argument(
                "--repo-url", help="Public GitHub URL to include in the submission note"
            )
        if name == "rank":
            p.add_argument(
                "--profile",
                type=Path,
                required=True,
                help="Saved extraction tied to this transcript",
            )
    args = parser.parse_args()
    for name in ["openai", "httpx", "httpcore"]:
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        conversation, loads = read_inputs(args.workbook)
        if args.command == "rank":
            profile, document = read_profile(args.profile, conversation)
        else:
            document = extract(conversation, args.model)
            profile = DriverProfile.model_validate(document["profile"])
        if args.command == "extract":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n"
            )
            print(f"Saved evidence-backed extraction to {args.output}")
            return
        result = rank_loads(profile, loads, args.assumed_capacity_lb)
        write_outputs(
            args.workbook, args.output_dir, profile, document, result, args.repo_url
        )
        print(
            f"Mode: {result['mode']}; {len(result['top_three'])} ranked loads. Outputs: {args.output_dir}"
        )
        for index, row in enumerate(result["top_three"], 1):
            print(
                f"{index}. {row['load_id']} ${row['effective_rate_per_mile']:.3f}/mile"
            )
        if result["mode"] == "needs_capacity":
            print(
                "Capacity is unknown. Supply --assumed-capacity-lb only to generate a clearly labeled conditional scenario."
            )
    except ExtractionError as exc:
        parser.exit(2, f"{exc}\n")
    except (ValueError, KeyError, OSError) as exc:
        # Do not print raw exception strings: validation/API payloads may contain sensitive data.
        parser.exit(
            2,
            f"Input/output validation failed ({type(exc).__name__}). Check workbook, evidence, paths, and capacity arguments.\n",
        )


if __name__ == "__main__":
    main()
