"""Audit every API route for its auth gate and its rate limit.

A route that ships without a limit, or a Pro route that ships without the
entitlement dependency, is the kind of mistake that is invisible in review and
expensive in production. Run this before a release.

Run from api/:  python scripts_dev/audit_routes.py
"""

from __future__ import annotations

import ast
import pathlib
import sys

ROUTES = pathlib.Path("overtake/routes")
SKIP = {"__init__.py", "deps.py", "schemas.py"}

# Routes that are deliberately ungated, with the reason.
INTENTIONALLY_PUBLIC = {
    "/health": "liveness probe",
    "/leagues/{league_id}": "the free hook — must work with no account",
    "/leagues/{league_id}/rivals/{entry_id}/dossier": "the aha moment, free tier",
    "/auth/magic-link": "sign-in entry point",
    "/auth/callback": "sign-in callback",
    "/players/{slug}": "public SEO page",
    "/players": "public SEO index",
    "/gameweeks/{gameweek}": "public SEO page",
    "/teams/{slug}": "public SEO page",
    "/meta/season": "public site metadata",
    "/fpl/manager/{entry_id}": "public manager lookup",
    "/analytics/event": "cookieless funnel counting",
    "/webhooks/stripe": "authenticated by Stripe signature, not by cookie",
}


def gate_for(node: ast.AsyncFunctionDef | ast.FunctionDef) -> str:
    annotations = " ".join(
        ast.unparse(arg.annotation)
        for arg in [*node.args.args, *node.args.kwonlyargs]
        if arg.annotation is not None
    )
    if "RequirePro" in annotations:
        return "PRO"
    if "CurrentUser" in annotations:
        return "AUTH"
    if "OptionalUser" in annotations:
        return "optional"
    return "public"


def main() -> int:
    problems: list[str] = []
    rows: list[tuple[str, str, str, bool]] = []

    for path in sorted(ROUTES.glob("*.py")):
        if path.name in SKIP:
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if not (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name)
                    and decorator.func.value.id == "router"
                ):
                    continue
                method = decorator.func.attr.upper()
                route = (
                    decorator.args[0].value
                    if decorator.args and isinstance(decorator.args[0], ast.Constant)
                    else "?"
                )
                prefix = _router_prefix(tree)
                full = f"{prefix}{route}".replace("//", "/").rstrip("/") or "/"
                decorator_src = ast.get_source_segment(source, decorator) or ""
                limited = "rate_limit(" in decorator_src
                gate = gate_for(node)
                rows.append((method, full, gate, limited))

                if not limited:
                    problems.append(f"{method} {full} has no rate limit")
                if gate == "public" and full not in INTENTIONALLY_PUBLIC:
                    problems.append(f"{method} {full} is public with no recorded reason")

    print(f"{'METHOD':7} {'ROUTE':52} {'GATE':9} LIMIT")
    print("-" * 78)
    for method, route, gate, limited in sorted(rows, key=lambda r: r[1]):
        print(f"{method:7} {route:52} {gate:9} {'yes' if limited else 'NO'}")

    print(f"\n{len(rows)} routes")
    if problems:
        print("\nPROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("Every route has a rate limit, and every public route has a reason.")
    return 0


def _router_prefix(tree: ast.Module) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == "APIRouter":
                for keyword in node.value.keywords:
                    if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                        return str(keyword.value.value)
    return ""


if __name__ == "__main__":
    sys.exit(main())
