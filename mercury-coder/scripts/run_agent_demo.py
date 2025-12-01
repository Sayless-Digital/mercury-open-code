#!/usr/bin/env python3
"""
Utility script to exercise the delegate agent HTTP APIs.

Example:
    python scripts/run_agent_demo.py --goal "Summarize the repo" --project-path /path/to/project
"""

import argparse
import sys
import time

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Mercury Coder agent task from the CLI.")
    parser.add_argument("--goal", required=True, help="Natural language goal for the agent.")
    parser.add_argument(
        "--project-path",
        required=True,
        help="Absolute path to the project the agent should operate on.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Mercury backend base URL (default: http://127.0.0.1:8000).",
    )
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between status polls.")
    return parser.parse_args()


def http_post(client: httpx.Client, base_url: str, path: str, payload: dict):
    response = client.post(f"{base_url}{path}", json=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()


def http_get(client: httpx.Client, base_url: str, path: str):
    response = client.get(f"{base_url}{path}", timeout=30.0)
    response.raise_for_status()
    return response.json()


def main():
    args = parse_args()
    with httpx.Client() as client:
        print("Indexing project context...")
        index_result = http_post(
            client,
            args.base_url,
            "/api/agent/context/index",
            {"project_path": args.project_path, "max_files": 2000},
        )
        print(f"Indexed {index_result.get('files_indexed', 0)} files.")

        print("Starting agent run...")
        run_result = http_post(
            client,
            args.base_url,
            "/api/agent/run",
            {"goal": args.goal, "context": {"projectPath": args.project_path}},
        )
        task = run_result.get("task")
        if not task:
            print("Failed to create agent task:", run_result)
            sys.exit(1)
        task_id = task["id"]
        print(f"Task {task_id} created. Polling for completion...")

        while True:
            time.sleep(args.poll_interval)
            detail = http_get(client, args.base_url, f"/api/agent/tasks/{task_id}")
            task = detail.get("task", {})
            status = task.get("status")
            print(f"Status: {status}")
            if status in {"success", "error"}:
                break

        print("\n=== Final Result ===")
        result = task.get("result") or {}
        print(result.get("summary", "No summary returned."))
        if result.get("plan"):
            print("\nPlan:\n", result["plan"])
        print("\nEvents:")
        for event in task.get("events", []):
            print(f"- [{event.get('type')}] {event.get('message')}")


if __name__ == "__main__":
    main()


