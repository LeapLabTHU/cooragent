import argparse
import asyncio
import sys
from pathlib import Path
import logging

# Ensure 'src' package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.evaluation.manager import EvaluationManager  # noqa: E402
from src.interface.evaluation import EvaluationConfig  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run Cooragent benchmark evaluation via Python API")
    parser.add_argument("--benchmark", "-b", default="gaia", help="Benchmark to run (default: gaia)")
    parser.add_argument("--subset", "-s", default="2023_level1", help="Dataset subset or split")
    parser.add_argument("--limit", "-l", type=int, default=None, help="Limit number of tasks to run")
    parser.add_argument("--max-concurrent", type=int, default=5, help="Max concurrent tasks")
    parser.add_argument("--timeout", type=int, default=300, help="Per-task timeout (seconds)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable INFO logging")
    parser.add_argument("--debug", action="store_true", help="Enable DEBUG logging")
    parser.add_argument("--debug-eval", action="store_true", help="Enable evaluation debug mode with per-task pretty output and transcript saving")
    parser.add_argument("--output-dir", default="./store/evaluation", help="Directory to save evaluation outputs (results/reports/transcripts)")
    args = parser.parse_args()

    # Configure logging (force override any prior config)
    # Default to INFO if no flag is provided so users see progress by default.
    level = logging.DEBUG if args.debug else (logging.INFO if args.verbose else logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s", force=True)

    mgr = EvaluationManager()
    cfg = EvaluationConfig(
        benchmark=args.benchmark,
        subset=args.subset,
        limit=args.limit,
        max_concurrent_tasks=args.max_concurrent,
        timeout_per_task=args.timeout,
        output_dir=args.output_dir,
        debug_eval=args.debug_eval,
        save_details=True,
        pretty_console=True,
    )

    result = await mgr.run_evaluation(args.benchmark, cfg)
    print(f"Run ID: {result.run_id}")
    print(f"Benchmark: {result.benchmark}")
    print(f"Tasks: {result.num_tasks}")
    print(f"Aggregate Score: {result.metrics.aggregate_score:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main())) 