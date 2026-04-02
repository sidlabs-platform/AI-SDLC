#!/usr/bin/env python3
"""
Compute execution waves from the task dependency graph.

Reads backlog/dependency-graph.json, validates the DAG, topologically sorts
tasks into waves, classifies tasks as backend/frontend, and generates:
  - backlog/execution-plan.md (human-readable)
  - backlog/wave-state.json  (machine-readable)
  - Updates backlog/tasks/TASK-*.md with wave numbers
  - Updates docs/change-log.md

Usage:
    python scripts/compute-waves.py \
        --tracker-issue 1 \
        --triggering-pr 7 \
        [--graph backlog/dependency-graph.json]
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_graph(path: str) -> dict[str, Any]:
    """Load and return the dependency graph JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_dag(graph: dict[str, Any]) -> list[str]:
    """Validate the dependency graph. Returns a list of error messages."""
    errors: list[str] = []
    tasks = graph.get("tasks", {})
    task_ids = set(tasks.keys())

    for task_id, task in tasks.items():
        # Check for missing dependency references
        for dep in task.get("depends_on", []):
            if dep not in task_ids:
                errors.append(
                    f"{task_id} depends on {dep} which is not defined in the graph"
                )

    # Check for circular dependencies via DFS
    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(node: str) -> bool:
        if node in in_stack:
            return True  # cycle detected
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for dep in tasks.get(node, {}).get("depends_on", []):
            if dep in task_ids and dfs(dep):
                errors.append(f"Circular dependency detected involving {node}")
                return True
        in_stack.discard(node)
        return False

    for task_id in task_ids:
        if task_id not in visited:
            dfs(task_id)

    return errors


def compute_waves(graph: dict[str, Any], tasks: dict[str, dict]) -> dict[int, list[str]]:
    """Extract wave assignments from the dependency graph.

    The graph already contains curated wave groupings (tasks may share a wave
    even when one depends on the other — they're implemented sequentially
    within the wave). We validate that no task's dependencies span a later wave,
    then return the existing assignments.

    Falls back to strict topological sort only if the graph has no wave data.
    """
    # Try to use pre-existing wave assignments from the graph
    graph_waves = graph.get("waves", {})
    if graph_waves:
        waves: dict[int, list[str]] = {}
        for wave_key, wave_info in graph_waves.items():
            wave_num = int(wave_key)
            waves[wave_num] = sorted(wave_info.get("tasks", []))

        # Validate: every task's dependencies must be in the same or earlier wave
        task_wave_map = {}
        for wave_num, task_ids in waves.items():
            for tid in task_ids:
                task_wave_map[tid] = wave_num

        warnings = []
        for wave_num, task_ids in waves.items():
            for tid in task_ids:
                for dep in tasks.get(tid, {}).get("depends_on", []):
                    dep_wave = task_wave_map.get(dep)
                    if dep_wave is not None and dep_wave > wave_num:
                        warnings.append(
                            f"{tid} (wave {wave_num}) depends on {dep} "
                            f"(wave {dep_wave}) — dependency in a later wave"
                        )
        if warnings:
            print("⚠️  Wave assignment warnings:", file=sys.stderr)
            for w in warnings:
                print(f"   - {w}", file=sys.stderr)

        return dict(sorted(waves.items()))

    # Fallback: strict topological sort
    task_ids = set(tasks.keys())
    assigned: dict[str, int] = {}
    waves_computed: dict[int, list[str]] = defaultdict(list)

    max_iterations = len(task_ids) + 1
    for _ in range(max_iterations):
        progress = False
        for task_id in sorted(task_ids):
            if task_id in assigned:
                continue
            deps = [d for d in tasks[task_id].get("depends_on", []) if d in task_ids]
            if not deps:
                assigned[task_id] = 0
                waves_computed[0].append(task_id)
                progress = True
            elif all(d in assigned for d in deps):
                wave = max(assigned[d] for d in deps) + 1
                assigned[task_id] = wave
                waves_computed[wave].append(task_id)
                progress = True
        if not progress:
            break

    unassigned = task_ids - set(assigned.keys())
    if unassigned:
        print(f"WARNING: {len(unassigned)} tasks could not be assigned to waves: "
              f"{sorted(unassigned)}", file=sys.stderr)

    return dict(sorted(waves_computed.items()))


def classify_task_type(task_id: str, task: dict, tasks_dir: Path) -> str:
    """Classify a task as 'backend' or 'frontend' by inspecting its task file."""
    task_file = tasks_dir / f"{task_id}.md"
    if task_file.exists():
        content = task_file.read_text(encoding="utf-8").lower()
        frontend_indicators = [
            "src/templates/", "src/static/", ".html", ".css", ".js",
            "template", "stylesheet", "frontend", "jinja2",
            "responsive layout", "page"
        ]
        # Check if the task primarily creates frontend files
        files_section = ""
        in_files = False
        for line in content.split("\n"):
            if "files to create" in line or "files to modify" in line:
                in_files = True
                continue
            if in_files and line.strip().startswith("- "):
                files_section += line + "\n"
            elif in_files and line.strip() and not line.strip().startswith("- "):
                in_files = False

        if files_section:
            has_frontend = any(ind in files_section for ind in
                             ["src/templates/", "src/static/", ".html", ".css"])
            has_backend = any(ind in files_section for ind in
                            ["src/auth/", "src/courses/", "src/ai/",
                             "src/progress/", "src/reporting/",
                             "src/config", "src/main", "src/database",
                             "requirements.txt", "tests/"])
            if has_frontend and not has_backend:
                return "frontend"

    return "backend"


def generate_wave_theme(wave_num: int, task_ids: list[str],
                        tasks: dict[str, dict],
                        graph_waves: dict[str, Any] | None = None) -> str:
    """Generate a short theme name for a wave based on its tasks."""
    # Use description from graph if available
    if graph_waves and str(wave_num) in graph_waves:
        desc = graph_waves[str(wave_num)].get("description", "")
        if desc:
            # Extract the short theme before the em-dash or first comma
            theme = desc.split("—")[0].strip().rstrip(" ")
            if theme:
                return theme

    theme_map = {
        0: "Foundation",
        1: "Core Infrastructure",
        2: "Service Layer & Endpoints",
        3: "Advanced Features & UI",
        4: "Admin Frontend",
    }
    return theme_map.get(wave_num, f"Wave {wave_num}")


def generate_branch_name(wave_num: int, theme: str) -> str:
    """Generate a branch name from wave number and theme."""
    slug = re.sub(r"[^a-z0-9]+", "-", theme.lower()).strip("-")
    return f"wave-{wave_num}/{slug}"


def generate_wave_state(waves: dict[int, list[str]], tasks: dict[str, dict],
                        tasks_dir: Path, graph: dict[str, Any],
                        tracker_issue: str,
                        triggering_issue: str) -> dict[str, Any]:
    """Generate the wave-state.json structure."""
    total_tasks = sum(len(tids) for tids in waves.values())
    all_backend = 0
    all_frontend = 0
    graph_waves = graph.get("waves", {})

    wave_entries = {}
    for wave_num in sorted(waves.keys()):
        task_ids = waves[wave_num]
        theme = generate_wave_theme(wave_num, task_ids, tasks, graph_waves)
        branch = generate_branch_name(wave_num, theme)

        backend_tasks = []
        frontend_tasks = []
        for tid in task_ids:
            task_type = classify_task_type(tid, tasks.get(tid, {}), tasks_dir)
            if task_type == "frontend":
                frontend_tasks.append(tid)
            else:
                backend_tasks.append(tid)

        all_backend += len(backend_tasks)
        all_frontend += len(frontend_tasks)

        depends_on = list(range(wave_num)) if wave_num > 0 else []

        wave_entries[str(wave_num)] = {
            "status": "pending",
            "theme": theme,
            "branch": branch,
            "tasks": sorted(task_ids),
            "backend_tasks": sorted(backend_tasks),
            "frontend_tasks": sorted(frontend_tasks),
            "depends_on_waves": depends_on,
            "pr_number": None,
            "issue_number": None,
            "completed_at": None,
        }

    return {
        "metadata": {
            "total_waves": len(waves),
            "total_tasks": total_tasks,
            "backend_tasks": all_backend,
            "frontend_tasks": all_frontend,
            "created_by": "sdlc-build-planner-workflow",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pipeline_tracker": f"#{tracker_issue}" if tracker_issue else None,
            "triggering_issue": f"#{triggering_issue}" if triggering_issue else None,
            "source_graph": "backlog/dependency-graph.json",
        },
        "waves": wave_entries,
    }


def generate_execution_plan(wave_state: dict[str, Any],
                            tasks: dict[str, dict]) -> str:
    """Generate the human-readable execution-plan.md content."""
    lines = [
        "# Execution Plan",
        "",
        f"Generated from `backlog/dependency-graph.json` by the build-planner workflow.",
        "",
        f"**Total waves**: {wave_state['metadata']['total_waves']}  ",
        f"**Total tasks**: {wave_state['metadata']['total_tasks']}  ",
        f"**Backend tasks**: {wave_state['metadata']['backend_tasks']}  ",
        f"**Frontend tasks**: {wave_state['metadata']['frontend_tasks']}  ",
        "",
    ]

    for wave_key in sorted(wave_state["waves"].keys(), key=int):
        wave = wave_state["waves"][wave_key]
        wave_num = int(wave_key)
        theme = wave["theme"]
        branch = wave["branch"]

        deps_str = ", ".join(f"Wave {d}" for d in wave["depends_on_waves"])
        if not deps_str:
            deps_str = "no dependencies"

        lines.append(f"## Wave {wave_num} — {theme} ({deps_str})")
        lines.append(f"**Branch:** `{branch}`")
        lines.append("")

        # Backend tasks table
        lines.append("### Backend Tasks")
        if wave["backend_tasks"]:
            lines.append("| Task ID  | Title | Dependencies |")
            lines.append("|----------|-------|--------------|")
            for tid in wave["backend_tasks"]:
                t = tasks.get(tid, {})
                title = t.get("title", "Unknown")
                deps = ", ".join(t.get("depends_on", [])) or "—"
                lines.append(f"| {tid} | {title} | {deps} |")
        else:
            lines.append("_None in this wave_")
        lines.append("")

        # Frontend tasks table
        lines.append("### Frontend Tasks")
        if wave["frontend_tasks"]:
            lines.append("| Task ID  | Title | Dependencies |")
            lines.append("|----------|-------|--------------|")
            for tid in wave["frontend_tasks"]:
                t = tasks.get(tid, {})
                title = t.get("title", "Unknown")
                deps = ", ".join(t.get("depends_on", [])) or "—"
                lines.append(f"| {tid} | {title} | {deps} |")
        else:
            lines.append("_None in this wave_")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def update_task_files(waves: dict[int, list[str]], tasks_dir: Path) -> int:
    """Update task markdown files with computed wave numbers. Returns count updated."""
    updated = 0
    for wave_num, task_ids in waves.items():
        for task_id in task_ids:
            task_file = tasks_dir / f"{task_id}.md"
            if not task_file.exists():
                print(f"  WARNING: {task_file} not found, skipping", file=sys.stderr)
                continue

            content = task_file.read_text(encoding="utf-8")
            # Check if Wave field already exists in the table
            if re.search(r"\*\*Wave\*\*", content):
                # Update existing wave field
                content = re.sub(
                    r"(\| \*\*Wave\*\*\s*\|)\s*[^|]*\|",
                    f"\\1 {wave_num}              |",
                    content,
                )
            else:
                # Add Wave field after Estimate row in the metadata table
                content = re.sub(
                    r"(\| \*\*Estimate\*\*\s*\|[^|]*\|)",
                    f"\\1\n| **Wave**     | {wave_num}                 |",
                    content,
                )
            task_file.write_text(content, encoding="utf-8")
            updated += 1
    return updated


def update_changelog(repo_root: Path, wave_state: dict[str, Any],
                     tracker_issue: str) -> None:
    """Append build planning entry to docs/change-log.md."""
    changelog = repo_root / "docs" / "change-log.md"
    if not changelog.exists():
        changelog.parent.mkdir(parents=True, exist_ok=True)
        changelog.write_text("# Change Log\n\n", encoding="utf-8")

    content = changelog.read_text(encoding="utf-8")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    meta = wave_state["metadata"]

    entry = (
        f"\n## {today} — Build Planning (Automated)\n\n"
        f"- **Stage**: 3.5 — Build Planning\n"
        f"- **Executor**: `sdlc-build-planner` workflow (automated)\n"
        f"- **Pipeline Tracker**: #{tracker_issue}\n"
        f"- **Waves computed**: {meta['total_waves']}\n"
        f"- **Total tasks**: {meta['total_tasks']} "
        f"({meta['backend_tasks']} backend, {meta['frontend_tasks']} frontend)\n"
        f"- **Artifacts**: `backlog/execution-plan.md`, `backlog/wave-state.json`\n"
        f"- All task files updated with wave assignments\n"
    )

    # Insert after the first heading
    if "\n## " in content:
        # Insert before the first ## entry
        idx = content.index("\n## ", content.index("\n") + 1)
        content = content[:idx] + entry + content[idx:]
    else:
        content += entry

    changelog.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute execution waves from the task dependency graph."
    )
    parser.add_argument(
        "--graph",
        default="backlog/dependency-graph.json",
        help="Path to dependency-graph.json (default: backlog/dependency-graph.json)",
    )
    parser.add_argument(
        "--tracker-issue",
        default="",
        help="Pipeline tracker issue number (e.g., 1)",
    )
    parser.add_argument(
        "--triggering-pr",
        default="",
        help="PR number that triggered this run (e.g., 7)",
    )
    args = parser.parse_args()

    repo_root = Path(args.graph).resolve().parent.parent
    tasks_dir = repo_root / "backlog" / "tasks"

    # 1. Load graph
    print(f"📖 Loading dependency graph from {args.graph}...")
    graph = load_graph(args.graph)
    tasks = graph.get("tasks", {})
    print(f"   Found {len(tasks)} tasks")

    # 2. Validate
    print("🔍 Validating DAG...")
    errors = validate_dag(graph)
    if errors:
        print("❌ Validation failed:")
        for err in errors:
            print(f"   - {err}")
        sys.exit(1)
    print("   ✅ DAG is valid")

    # 3. Compute waves
    print("📊 Computing execution waves...")
    waves = compute_waves(graph, tasks)
    for wave_num in sorted(waves.keys()):
        print(f"   Wave {wave_num}: {len(waves[wave_num])} tasks")

    # 4. Generate wave-state.json
    print("📝 Generating wave-state.json...")
    wave_state = generate_wave_state(
        waves, tasks, tasks_dir, graph,
        args.tracker_issue, args.triggering_pr,
    )
    wave_state_path = repo_root / "backlog" / "wave-state.json"
    with open(wave_state_path, "w", encoding="utf-8") as f:
        json.dump(wave_state, f, indent=2)
    print(f"   ✅ Written to {wave_state_path}")

    # 5. Generate execution-plan.md
    print("📝 Generating execution-plan.md...")
    plan_content = generate_execution_plan(wave_state, tasks)
    plan_path = repo_root / "backlog" / "execution-plan.md"
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_content)
    print(f"   ✅ Written to {plan_path}")

    # 6. Update task files
    print("📝 Updating task files with wave numbers...")
    updated = update_task_files(waves, tasks_dir)
    print(f"   ✅ Updated {updated} task files")

    # 7. Update change log
    print("📝 Updating change log...")
    update_changelog(repo_root, wave_state, args.tracker_issue)
    print("   ✅ Change log updated")

    # Summary
    meta = wave_state["metadata"]
    print()
    print("🎉 Build planning complete!")
    print(f"   Waves: {meta['total_waves']}")
    print(f"   Tasks: {meta['total_tasks']} ({meta['backend_tasks']} backend, "
          f"{meta['frontend_tasks']} frontend)")


if __name__ == "__main__":
    main()
