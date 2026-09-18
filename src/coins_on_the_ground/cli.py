from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from coins_on_the_ground.adapters import (
    CapabilityObservation,
    adapt_bridge_mesh_advertisement,
    adapt_machine_bridge_registration,
    estimate_against_inventory,
)
from coins_on_the_ground.estimation import (
    Capability,
    CapabilityProfile,
    FeasibilityClass,
    ProfitabilityClass,
)
from coins_on_the_ground.evidence import (
    append_evidence_ledger,
    collect_sources_report,
    detect_evidence_drift,
    load_evidence_ledger,
    materialize_acquisition_catalog,
    parse_collected_record,
    parse_evidence_sources,
    parse_materialization_policy,
    summarize_evidence_stability,
)
from coins_on_the_ground.opportunity import Opportunity, review_and_deduplicate
from coins_on_the_ground.planning import (
    assess_evidence,
    assess_historical_confidence_many,
    parse_acquisition_catalog,
    parse_historical_confidence_policy,
    plan_capability_acquisition,
    plan_capability_gap,
)
from coins_on_the_ground.scouts import (
    AlgoraScout,
    FranticBountyScout,
    GitHubBountyScout,
    IssueHuntScout,
    Scout,
    parse_scout_source_registry,
)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def serialize(opportunity: Opportunity) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in asdict(opportunity).items()} | {
        "expected_net_value": _json_value(opportunity.expected_net_value),
        "execution_candidate": opportunity.execution_candidate,
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[object]:
    rows: list[object] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _collection_records_from_rows(rows: list[object]) -> list[Any]:
    records = []
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise TypeError("collection JSONL rows must be objects")
        if raw_row.get("status") != "success":
            continue
        records.append(parse_collected_record(raw_row.get("record")))
    return records


async def _collect(scout: Scout) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    async for opportunity in scout.discover():
        opportunities.append(opportunity)
    return opportunities


def _scouts_for_source(source: str, limit: int) -> list[Scout]:
    if source == "frantic":
        return [FranticBountyScout(limit=limit)]
    if source == "github-bounties":
        return [GitHubBountyScout(limit=limit)]
    if source == "issuehunt":
        return [IssueHuntScout(limit=limit)]
    if source == "algora":
        return [AlgoraScout(limit=limit)]
    return [
        FranticBountyScout(limit=limit),
        GitHubBountyScout(limit=limit),
        IssueHuntScout(limit=limit),
        AlgoraScout(limit=limit),
    ]


async def _discover(source: str, limit: int) -> list[Opportunity]:
    scouts = _scouts_for_source(source, limit)
    batches = await asyncio.gather(*(_collect(scout) for scout in scouts))
    return [opportunity for batch in batches for opportunity in batch]


async def _emit_scan(scout: Scout, args: argparse.Namespace) -> int:
    opportunities = await _collect(scout)
    rows = [serialize(opportunity) for opportunity in opportunities]

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "scout": scout.name,
                "candidates": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


async def _scan_github(args: argparse.Namespace) -> int:
    return await _emit_scan(
        GitHubBountyScout(query=args.query, limit=args.limit),
        args,
    )


async def _scan_frantic(args: argparse.Namespace) -> int:
    return await _emit_scan(FranticBountyScout(limit=args.limit), args)


async def _scan_issuehunt(args: argparse.Namespace) -> int:
    return await _emit_scan(IssueHuntScout(limit=args.limit), args)


async def _scan_algora(args: argparse.Namespace) -> int:
    orgs = tuple(args.org) if args.org else None
    return await _emit_scan(AlgoraScout(limit=args.limit, orgs=orgs), args)


async def _sources_check(args: argparse.Namespace) -> int:
    registry_value = await asyncio.to_thread(_load_json, Path(args.registry))
    sources = parse_scout_source_registry(registry_value)

    rows = [
        {
            "source_id": source.source_id,
            "display_name": source.display_name,
            "base_url": source.base_url,
            "network_surface": source.network_surface.value,
            "country": source.country,
            "jurisdiction": source.jurisdiction,
            "categories": list(source.categories),
            "enabled": source.enabled,
            "notes": source.notes,
        }
        for source in sources
    ]

    for row in rows:
        print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "scout-source-registry",
                "sources": len(sources),
                "enabled_sources": sum(1 for source in sources if source.enabled),
                "onion_sources": sum(
                    1 for source in sources if source.network_surface.value == "onion"
                ),
                "execution_performed": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


async def _review(args: argparse.Namespace) -> int:
    scouts = _scouts_for_source(args.source, args.limit)
    opportunities = await _discover(args.source, args.limit)
    reviews = review_and_deduplicate(opportunities)

    rows = [
        {
            "fingerprint": review.fingerprint,
            "review_score": review.review_score,
            "score_breakdown": review.score_breakdown,
            "review_allowed": review.review_allowed,
            "review_reason": review.review_reason,
            "opportunity": serialize(review.opportunity),
        }
        for review in reviews
    ]

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "opportunity-review",
                "sources": [scout.name for scout in scouts],
                "raw_candidates": len(opportunities),
                "deduplicated_candidates": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


def _manual_observation(args: argparse.Namespace) -> CapabilityObservation:
    declared = frozenset(Capability(value) for value in args.capability)
    return CapabilityObservation(
        source_type="manual",
        source_id=args.profile_name,
        profile=CapabilityProfile(
            name=args.profile_name,
            capabilities=declared,
            hourly_cost_usd=args.hourly_cost_usd,
            configured=bool(declared),
        ),
        raw_capabilities=tuple(sorted(capability.value for capability in declared)),
        unmapped_capabilities=(),
    )


async def _load_observations(args: argparse.Namespace) -> list[CapabilityObservation]:
    observations: list[CapabilityObservation] = []

    for path_value in args.machine_bridge_registration:
        value = await asyncio.to_thread(_load_json, Path(path_value))
        observations.append(
            adapt_machine_bridge_registration(
                value,
                hourly_cost_usd=args.hourly_cost_usd,
            )
        )

    for path_value in args.mesh_advertisement:
        value = await asyncio.to_thread(_load_json, Path(path_value))
        observations.append(
            adapt_bridge_mesh_advertisement(
                value,
                hourly_cost_usd=args.hourly_cost_usd,
            )
        )

    if args.capability:
        observations.append(_manual_observation(args))

    return observations


def _observation_row(observation: CapabilityObservation) -> dict[str, Any]:
    return {
        "source_type": observation.source_type,
        "source_id": observation.source_id,
        "profile": {
            "name": observation.profile.name,
            "configured": observation.profile.configured,
            "capabilities": sorted(
                capability.value for capability in observation.profile.capabilities
            ),
            "hourly_cost_usd": _json_value(observation.profile.hourly_cost_usd),
        },
        "raw_capabilities": list(observation.raw_capabilities),
        "unmapped_capabilities": list(observation.unmapped_capabilities),
        "reachable_capabilities": list(observation.reachable_capabilities),
        "heartbeat_at": observation.heartbeat_at,
    }


async def _inspect_capabilities(args: argparse.Namespace) -> int:
    observations = await _load_observations(args)
    rows = [_observation_row(observation) for observation in observations]

    for row in rows:
        print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "capability-adapter",
                "profiles": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


def _profile_estimate_row(item: Any) -> dict[str, Any]:
    return {
        "observation": _observation_row(item.observation),
        "estimate": _json_value(asdict(item.estimate)),
    }


def _estimate_sort_key(row: dict[str, Any]) -> tuple[int, int, int, int]:
    profitability_rank = {
        ProfitabilityClass.POSITIVE.value: 3,
        ProfitabilityClass.UNCERTAIN.value: 2,
        ProfitabilityClass.UNKNOWN.value: 1,
        ProfitabilityClass.NEGATIVE.value: 0,
    }
    feasibility_rank = {
        FeasibilityClass.FEASIBLE.value: 3,
        FeasibilityClass.PARTIAL.value: 2,
        FeasibilityClass.UNKNOWN.value: 1,
        FeasibilityClass.NOT_FEASIBLE.value: 0,
    }
    best = row["best_profile"]
    if best is None:
        return int(row["review_allowed"]), 0, 0, int(row["review_score"])

    estimate = best["estimate"]
    return (
        int(row["review_allowed"]),
        feasibility_rank[str(estimate["feasibility"])],
        profitability_rank[str(estimate["profitability"])],
        int(row["review_score"]),
    )


async def _estimate(args: argparse.Namespace) -> int:
    observations = await _load_observations(args)
    opportunities = await _discover(args.source, args.limit)
    reviews = review_and_deduplicate(opportunities)

    rows: list[dict[str, Any]] = []
    for review in reviews:
        profile_estimates = estimate_against_inventory(
            review.opportunity,
            observations,
        )
        serialized_estimates = [
            _profile_estimate_row(item) for item in profile_estimates
        ]
        rows.append(
            {
                "fingerprint": review.fingerprint,
                "review_score": review.review_score,
                "review_allowed": review.review_allowed,
                "review_reason": review.review_reason,
                "best_profile": serialized_estimates[0] if serialized_estimates else None,
                "profile_estimates": serialized_estimates,
                "opportunity": serialize(review.opportunity),
            }
        )

    rows.sort(key=_estimate_sort_key, reverse=True)

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "cost-feasibility-estimator",
                "profiles": len(observations),
                "raw_candidates": len(opportunities),
                "deduplicated_candidates": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


async def _gaps(args: argparse.Namespace) -> int:
    observations = await _load_observations(args)
    opportunities = await _discover(args.source, args.limit)
    reviews = review_and_deduplicate(opportunities)

    rows: list[dict[str, Any]] = []
    for review in reviews:
        plan = plan_capability_gap(review.opportunity, observations)
        rows.append(
            {
                "fingerprint": review.fingerprint,
                "review_score": review.review_score,
                "review_allowed": review.review_allowed,
                "review_reason": review.review_reason,
                "gap_plan": _json_value(asdict(plan)),
                "opportunity": serialize(review.opportunity),
            }
        )

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "capability-gap-planner",
                "profiles": len(observations),
                "raw_candidates": len(opportunities),
                "deduplicated_candidates": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


async def _evidence_collect(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config_value = await asyncio.to_thread(_load_json, config_path)
    sources = parse_evidence_sources(config_value)
    report = await collect_sources_report(
        sources,
        local_root=config_path.parent,
    )

    rows: list[dict[str, Any]] = []
    for record in report.records:
        rows.append(
            {
                "status": "success",
                "record": _json_value(asdict(record)),
                "assessment": _json_value(
                    asdict(assess_evidence(record.descriptor.evidence))
                ),
            }
        )

    for failure in report.failures:
        rows.append(
            {
                "status": "failure",
                "failure": _json_value(asdict(failure)),
            }
        )

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "evidence-collector",
                "configured_sources": len(sources),
                "successful_records": len(report.records),
                "failures": len(report.failures),
                "execution_performed": False,
            }
        )
    )
    return 1 if report.failures else 0


async def _evidence_materialize(args: argparse.Namespace) -> int:
    collection_rows = await asyncio.to_thread(_load_jsonl, Path(args.records))
    records = _collection_records_from_rows(collection_rows)

    policy_value = await asyncio.to_thread(_load_json, Path(args.policy))
    rules = parse_materialization_policy(policy_value)
    report = materialize_acquisition_catalog(tuple(records), rules)

    parse_acquisition_catalog(report.catalog)
    await asyncio.to_thread(_write_json, Path(args.output), report.catalog)

    print(
        json.dumps(
            {
                "engine": "evidence-materializer",
                "records": len(records),
                "rules": len(rules),
                "catalog_options": len(report.catalog["options"]),
                "missing_source_ids": list(report.missing_source_ids),
                "unused_source_ids": list(report.unused_source_ids),
                "output": args.output,
                "execution_performed": False,
            },
            ensure_ascii=False,
        )
    )
    return 1 if report.missing_source_ids else 0


async def _evidence_ledger_append(args: argparse.Namespace) -> int:
    collection_rows = await asyncio.to_thread(_load_jsonl, Path(args.records))
    records = _collection_records_from_rows(collection_rows)
    report = await asyncio.to_thread(
        append_evidence_ledger,
        Path(args.ledger),
        tuple(records),
    )

    print(
        json.dumps(
            {
                "engine": "evidence-ledger-append",
                "records": len(records),
                "appended": report.appended,
                "duplicates": report.duplicates,
                "total_entries": report.total_entries,
                "ledger": args.ledger,
                "execution_performed": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


async def _evidence_ledger_analyze(args: argparse.Namespace) -> int:
    entries = await asyncio.to_thread(load_evidence_ledger, Path(args.ledger))
    drift = detect_evidence_drift(entries, source_id=args.source_id)
    summaries = summarize_evidence_stability(entries, source_id=args.source_id)

    rows = [
        {
            "type": "drift",
            "event": _json_value(asdict(event)),
        }
        for event in drift
    ]
    rows.extend(
        {
            "type": "summary",
            "summary": _json_value(asdict(summary)),
        }
        for summary in summaries
    )

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "evidence-ledger-analysis",
                "entries": len(entries),
                "sources": len(summaries),
                "drift_events": len(drift),
                "source_filter": args.source_id,
                "execution_performed": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


async def _historical_confidence(args: argparse.Namespace) -> int:
    entries = await asyncio.to_thread(load_evidence_ledger, Path(args.ledger))
    summaries = summarize_evidence_stability(entries, source_id=args.source_id)
    policy_value = await asyncio.to_thread(_load_json, Path(args.policy))
    policy = parse_historical_confidence_policy(policy_value)
    assessments = assess_historical_confidence_many(summaries, policy)

    rows = [
        {
            "source_id": source_id,
            "assessment": _json_value(asdict(assessment)),
        }
        for source_id, assessment in sorted(assessments.items())
    ]

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "historical-confidence",
                "ledger_entries": len(entries),
                "sources": len(assessments),
                "source_filter": args.source_id,
                "execution_performed": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


async def _catalog_check(args: argparse.Namespace) -> int:
    catalog_value = await asyncio.to_thread(_load_json, Path(args.catalog))
    options = parse_acquisition_catalog(catalog_value)

    fresh = 0
    rows: list[dict[str, Any]] = []
    for option in options:
        assessment = assess_evidence(option.evidence)
        if assessment.status.value == "FRESH":
            fresh += 1
        rows.append(
            {
                "option_id": option.option_id,
                "mode": option.mode.value,
                "provides": [capability.value for capability in option.provides],
                "enabled": option.enabled,
                "evidence_required": option.evidence_required,
                "evidence": _json_value(asdict(assessment)),
                "source_url": (
                    option.evidence.source_url if option.evidence is not None else None
                ),
                "authorization_requirements": (
                    list(option.evidence.authorization_requirements)
                    if option.evidence is not None
                    else []
                ),
            }
        )

    for row in rows:
        print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "acquisition-catalog-check",
                "options": len(options),
                "fresh_evidence_options": fresh,
                "execution_performed": False,
            }
        )
    )
    return 0


async def _acquisition_plan(args: argparse.Namespace) -> int:
    observations = await _load_observations(args)
    catalog_value = await asyncio.to_thread(_load_json, Path(args.catalog))
    options = parse_acquisition_catalog(catalog_value)

    if bool(args.ledger) != bool(args.historical_policy):
        raise ValueError(
            "--ledger and --historical-policy must be provided together"
        )

    historical_confidence = None
    if args.ledger and args.historical_policy:
        entries = await asyncio.to_thread(load_evidence_ledger, Path(args.ledger))
        summaries = summarize_evidence_stability(entries)
        policy_value = await asyncio.to_thread(
            _load_json,
            Path(args.historical_policy),
        )
        policy = parse_historical_confidence_policy(policy_value)
        historical_confidence = assess_historical_confidence_many(
            summaries,
            policy,
        )

    opportunities = await _discover(args.source, args.limit)
    reviews = review_and_deduplicate(opportunities)

    rows: list[dict[str, Any]] = []
    for review in reviews:
        plan = plan_capability_acquisition(
            review.opportunity,
            observations,
            options,
            amortization_uses=args.amortization_uses,
            historical_confidence=historical_confidence,
        )
        rows.append(
            {
                "fingerprint": review.fingerprint,
                "review_score": review.review_score,
                "review_allowed": review.review_allowed,
                "review_reason": review.review_reason,
                "acquisition_plan": _json_value(asdict(plan)),
                "opportunity": serialize(review.opportunity),
            }
        )

    if args.output:
        await asyncio.to_thread(_write_jsonl, Path(args.output), rows)
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))

    print(
        json.dumps(
            {
                "engine": "capability-acquisition-planner",
                "profiles": len(observations),
                "catalog_options": len(options),
                "historical_confidence_sources": (
                    len(historical_confidence)
                    if historical_confidence is not None
                    else 0
                ),
                "amortization_uses": args.amortization_uses,
                "raw_candidates": len(opportunities),
                "deduplicated_candidates": len(rows),
                "execution_performed": False,
            }
        )
    )
    return 0


def _add_common_scan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--output", help="optional JSONL output path")


def _add_source_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "source",
        choices=("all", "frantic", "github-bounties", "issuehunt", "algora"),
        default="all",
        nargs="?",
    )


def _add_capability_profile_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile-name", default="cli-profile")
    parser.add_argument(
        "--capability",
        action="append",
        choices=tuple(capability.value for capability in Capability),
        default=[],
        help="declared local capability; repeat for multiple capabilities",
    )
    parser.add_argument(
        "--machine-bridge-registration",
        action="append",
        default=[],
        help="path to ARCA Machine Bridge worker registration JSON; repeat as needed",
    )
    parser.add_argument(
        "--mesh-advertisement",
        action="append",
        default=[],
        help="path to Bridge Mesh node advertisement JSON; repeat as needed",
    )
    parser.add_argument(
        "--hourly-cost-usd",
        type=Decimal,
        help="operating-cost assumption applied to imported profiles",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cog", description="Coins on the Ground Value Scout")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="discover read-only opportunity candidates")
    scan_sub = scan.add_subparsers(dest="source", required=True)

    github = scan_sub.add_parser("github-bounties", help="scan public GitHub bounty issues")
    github.add_argument(
        "--query",
        default="bounty in:title,body is:issue is:open",
        help="GitHub Issues search query",
    )
    _add_common_scan_args(github)
    github.set_defaults(handler=_scan_github)

    frantic = scan_sub.add_parser("frantic", help="scan structured Frantic bounty mirrors")
    _add_common_scan_args(frantic)
    frantic.set_defaults(handler=_scan_frantic)

    issuehunt = scan_sub.add_parser(
        "issuehunt",
        help="scan globally visible funded IssueHunt OSS tasks",
    )
    _add_common_scan_args(issuehunt)
    issuehunt.set_defaults(handler=_scan_issuehunt)

    algora = scan_sub.add_parser(
        "algora",
        help="scan public Algora bounty pages for configured organizations",
    )
    algora.add_argument(
        "--org",
        action="append",
        default=[],
        help="Algora organization handle; repeat to scan multiple organizations",
    )
    _add_common_scan_args(algora)
    algora.set_defaults(handler=_scan_algora)

    sources_check = subparsers.add_parser(
        "sources-check",
        help="validate and inspect a global scout source registry",
    )
    sources_check.add_argument(
        "--registry",
        required=True,
        help="path to cog-scout-source-registry-v1 JSON",
    )
    sources_check.set_defaults(handler=_sources_check)

    review = subparsers.add_parser(
        "review",
        help="score and deduplicate discovered opportunities for human review",
    )
    _add_source_argument(review)
    _add_common_scan_args(review)
    review.set_defaults(handler=_review)

    capabilities = subparsers.add_parser(
        "capabilities",
        help="inspect Machine Bridge / Bridge Mesh capability records",
    )
    _add_capability_profile_args(capabilities)
    capabilities.set_defaults(handler=_inspect_capabilities)

    estimate = subparsers.add_parser(
        "estimate",
        help="estimate cost and feasibility against declared/imported capability profiles",
    )
    _add_source_argument(estimate)
    _add_common_scan_args(estimate)
    _add_capability_profile_args(estimate)
    estimate.set_defaults(handler=_estimate)

    gaps = subparsers.add_parser(
        "gaps",
        help="explain missing or fragmented capabilities for discovered opportunities",
    )
    _add_source_argument(gaps)
    _add_common_scan_args(gaps)
    _add_capability_profile_args(gaps)
    gaps.set_defaults(handler=_gaps)

    acquisition = subparsers.add_parser(
        "acquisition-plan",
        help="plan how an explicit local catalog could close capability gaps",
    )
    _add_source_argument(acquisition)
    _add_common_scan_args(acquisition)
    _add_capability_profile_args(acquisition)
    acquisition.add_argument(
        "--catalog",
        required=True,
        help="path to a local capability acquisition catalog JSON",
    )
    acquisition.add_argument(
        "--amortization-uses",
        type=int,
        default=1,
        help="number of expected uses over which reusable setup cost is amortized",
    )
    acquisition.add_argument(
        "--ledger",
        help="optional local evidence ledger used for historical confidence",
    )
    acquisition.add_argument(
        "--historical-policy",
        help="historical confidence policy; requires --ledger",
    )
    acquisition.set_defaults(handler=_acquisition_plan)

    historical_confidence = subparsers.add_parser(
        "historical-confidence",
        help="evaluate ledger stability against an explicit historical policy",
    )
    historical_confidence.add_argument(
        "--ledger",
        required=True,
        help="local evidence ledger JSONL path",
    )
    historical_confidence.add_argument(
        "--policy",
        required=True,
        help="path to cog-historical-confidence-policy-v1 JSON",
    )
    historical_confidence.add_argument(
        "--source-id",
        help="optional source_id filter",
    )
    historical_confidence.add_argument(
        "--output",
        help="optional JSONL output path",
    )
    historical_confidence.set_defaults(handler=_historical_confidence)

    catalog_check = subparsers.add_parser(
        "catalog-check",
        help="inspect evidence freshness and claims in a local acquisition catalog",
    )
    catalog_check.add_argument(
        "--catalog",
        required=True,
        help="path to a local capability acquisition catalog JSON",
    )
    catalog_check.set_defaults(handler=_catalog_check)

    evidence_collect = subparsers.add_parser(
        "evidence-collect",
        help="collect versioned evidence from explicitly configured JSON sources",
    )
    evidence_collect.add_argument(
        "--config",
        required=True,
        help="path to a local cog-evidence-sources-v1 config JSON",
    )
    evidence_collect.add_argument(
        "--output",
        help="optional JSONL output path for collection records",
    )
    evidence_collect.set_defaults(handler=_evidence_collect)

    evidence_materialize = subparsers.add_parser(
        "evidence-materialize",
        help="materialize collected evidence into a new acquisition catalog v2",
    )
    evidence_materialize.add_argument(
        "--records",
        required=True,
        help="JSONL produced by cog evidence-collect --output",
    )
    evidence_materialize.add_argument(
        "--policy",
        required=True,
        help="path to a local cog-evidence-materialization-v1 policy",
    )
    evidence_materialize.add_argument(
        "--output",
        required=True,
        help="destination path for the generated acquisition catalog v2",
    )
    evidence_materialize.set_defaults(handler=_evidence_materialize)

    ledger_append = subparsers.add_parser(
        "evidence-ledger-append",
        help="append successful collected evidence records to a local append-only ledger",
    )
    ledger_append.add_argument(
        "--records",
        required=True,
        help="JSONL produced by cog evidence-collect --output",
    )
    ledger_append.add_argument(
        "--ledger",
        required=True,
        help="local append-only evidence ledger JSONL path",
    )
    ledger_append.set_defaults(handler=_evidence_ledger_append)

    ledger_analyze = subparsers.add_parser(
        "evidence-ledger-analyze",
        help="derive drift events and stability metrics from a local evidence ledger",
    )
    ledger_analyze.add_argument(
        "--ledger",
        required=True,
        help="local evidence ledger JSONL path",
    )
    ledger_analyze.add_argument(
        "--source-id",
        help="optional source_id filter",
    )
    ledger_analyze.add_argument(
        "--output",
        help="optional JSONL output path for drift and summaries",
    )
    ledger_analyze.set_defaults(handler=_evidence_ledger_analyze)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return asyncio.run(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
