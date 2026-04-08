#!/usr/bin/env python3
"""
status_cli.py — inspect and manage the enrichment pipeline status in MongoDB.

Usage examples
--------------
  # Show a summary of all status counts
  python status_cli.py summary

  # List artworks in ERROR state
  python status_cli.py list --status ENRICHMENT_ERROR

  # Reset ERROR artworks back to PENDING so they are retried
  python status_cli.py reset --from ENRICHMENT_ERROR --to PENDING_WIKIPEDIA

  # Reset a single artwork by objectId
  python status_cli.py reset --id 436535 --to PENDING_WIKIPEDIA

  # Mark artworks with no Wikidata URL as permanently skipped
  python status_cli.py reset --from NO_WIKIDATA --to NO_WIKIDATA   # (no-op, just confirms)
"""

import argparse
import os
import sys
from pymongo import MongoClient
from tabulate import tabulate   # pip install tabulate  (optional, falls back to plain print)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/")
MONGO_DB  = os.getenv("MONGO_DB",  "artemis_db")

ALL_STATUSES = [
    "PENDING_WIKIPEDIA",
    "ENRICHED",
    "NO_WIKIDATA",
    "ENRICHMENT_ERROR",
]


def get_collection():
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB]["status"]


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_summary(_args):
    col = get_collection()
    rows = []
    total = 0
    for status in ALL_STATUSES:
        count = col.count_documents({"status": status})
        total += count
        rows.append([status, count])
    rows.append(["─" * 25, "─" * 8])
    rows.append(["TOTAL", total])

    try:
        print(tabulate(rows, headers=["Status", "Count"], tablefmt="rounded_outline"))
    except Exception:
        for r in rows:
            print(f"  {r[0]:<30} {r[1]}")


def cmd_list(args):
    col = get_collection()
    status = args.status
    limit  = args.limit or 50
    docs   = list(col.find({"status": status}, {"objectId": 1, "_id": 0}).limit(limit))

    if not docs:
        print(f"No artworks with status '{status}'.")
        return

    print(f"\n{len(docs)} artworks with status '{status}' (limit={limit}):\n")
    for doc in docs:
        print(f"  objectId={doc['objectId']}")


def cmd_reset(args):
    col = get_collection()

    if args.id:
        result = col.update_one(
            {"objectId": int(args.id)},
            {"$set": {"status": args.to}},
        )
        if result.matched_count:
            print(f"objectId={args.id} → {args.to}")
        else:
            print(f"objectId={args.id} not found in status collection.")
        return

    if not args.from_status:
        print("Provide --from or --id.")
        sys.exit(1)

    count = col.count_documents({"status": args.from_status})
    if count == 0:
        print(f"No documents with status '{args.from_status}'.")
        return

    confirm = input(
        f"Reset {count} artworks from '{args.from_status}' → '{args.to}'? [y/N] "
    )
    if confirm.strip().lower() != "y":
        print("Aborted.")
        return

    result = col.update_many(
        {"status": args.from_status},
        {"$set": {"status": args.to}},
    )
    print(f"Updated {result.modified_count} documents → {args.to}")


# ── CLI parser ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Enrichment pipeline status CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # summary
    sub.add_parser("summary", help="Show counts for each status")

    # list
    p_list = sub.add_parser("list", help="List objectIds for a given status")
    p_list.add_argument("--status", required=True, choices=ALL_STATUSES)
    p_list.add_argument("--limit", type=int, default=50)

    # reset
    p_reset = sub.add_parser("reset", help="Change status for one or many artworks")
    p_reset.add_argument("--from", dest="from_status", help="Source status (bulk reset)")
    p_reset.add_argument("--id", help="Single objectId to reset")
    p_reset.add_argument("--to", required=True, choices=ALL_STATUSES)

    args = parser.parse_args()
    dispatch = {"summary": cmd_summary, "list": cmd_list, "reset": cmd_reset}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()