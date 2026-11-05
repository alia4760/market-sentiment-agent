import argparse
import logging
import sys

from agent import EXIT_CODES, agent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="rebuild today's newsletter even if one is already stored")
    parser.add_argument("--collect-only", action="store_true",
                        help="save the data but skip Jev scoring and don't store a newsletter")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)  # prices.py logs missing tickers itself

    result = agent.invoke({"refresh": args.refresh, "collect_only": args.collect_only})
    print(result["newsletter"])

    errors = result.get("errors", [])
    if result.get("from_store"):
        print("\n(reused today's stored newsletter)", file=sys.stderr)
    if not errors:
        logging.getLogger("main").info("Run finished cleanly")
    if errors:
        print("\nRun finished with errors:", file=sys.stderr)
        for err in errors:
            print(f"  [{err['stage']}] {err['message']}", file=sys.stderr)
        sys.exit(EXIT_CODES[errors[0]["stage"]])


if __name__ == "__main__":
    main()
