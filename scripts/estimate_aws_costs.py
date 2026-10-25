"""Reproducible Ohio estimates from a dated public AWS rate snapshot; no AWS calls."""

import argparse
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parents[1] / "infra/pricing/us-east-2-2026-10-25.json"


def estimate(catalog, architecture, *, hours=730, billable_egress_gb=10, log_ingest_gb=5):
    if catalog["region"] != "us-east-2" or catalog["currency"] != "USD":
        raise ValueError("Rates must be Ohio USD")
    if architecture not in {"simple", "managed"}:
        raise ValueError("Unknown architecture")
    quantities = [Decimal(str(value)) for value in (hours, billable_egress_gb, log_ingest_gb)]
    if any(not value.is_finite() or value < 0 for value in quantities):
        raise ValueError("Usage must be finite and nonnegative")
    hours, egress, logs = quantities
    rows = []

    def add(label, key, quantity, *, allowance=False):
        rate = Decimal(catalog["rates"][key]["usd"])
        if not rate.is_finite() or rate < 0:
            raise ValueError("Invalid unit price")
        rows.append(
            {
                "item": label,
                "rate_key": key,
                "quantity": str(quantity),
                "unit_price_usd": str(rate),
                "usd_unrounded": str(rate * Decimal(str(quantity))),
                "usage_allowance": allowance,
            }
        )

    add("EC2 t3.small Linux", "ec2_t3_small_hour", hours)
    add("30 GiB EC2 gp3 root disk", "ebs_gp3_gb_month", 30)
    add(
        "Public IPv4 (one EC2; managed adds two ALB addresses)",
        "public_ipv4_hour",
        hours * (3 if architecture == "managed" else 1),
    )
    if architecture == "managed":
        # Multi-AZ RDS hourly/storage prices already include the standby pair.
        add("RDS db.t4g.micro Multi-AZ pair", "rds_micro_multiaz_hour", hours)
        add("20 GiB RDS Multi-AZ gp3", "rds_multiaz_gp3_gb_month", 20)
        add("Two Redis cache.t4g.micro nodes", "redis_micro_hour", hours * 2)
        add("Application Load Balancer", "alb_hour", hours)
        add("Two Secrets Manager secrets (runtime and RDS admin)", "secret_month", 2)
        add("Example one average ALB LCU", "alb_lcu_hour", hours, allowance=True)
        add("Example log ingestion", "log_ingest_gb", logs, allowance=True)
        add("Example one GiB retained compressed logs", "log_storage_gb_month", 1, allowance=True)
        add("Example 1,000 secret API calls", "secret_api_request", 1000, allowance=True)
        add("Example 20 billable cross-AZ endpoint-GB", "regional_transfer_gb", 20, allowance=True)
    add(
        "Example billable internet egress beyond any free allowance",
        "internet_egress_gb",
        egress,
        allowance=True,
    )
    add(
        "Optional retained 30 GiB EBS snapshot (not provisioned by plan)",
        "ebs_snapshot_gb_month",
        30,
        allowance=True,
    )
    fixed = sum(
        (Decimal(row["usd_unrounded"]) for row in rows if not row["usage_allowance"]), Decimal(0)
    )
    total = sum((Decimal(row["usd_unrounded"]) for row in rows), Decimal(0))

    def money(value):
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    for row in rows:
        row["monthly_usd"] = money(Decimal(row["usd_unrounded"]))
    return {
        "architecture": architecture,
        "region": catalog["region"],
        "snapshot_date": catalog["retrieved_at"],
        "hours": str(hours),
        "fixed_monthly_usd": money(fixed),
        "example_monthly_usd": money(total),
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--architecture", choices=["simple", "managed", "both"], default="both")
    parser.add_argument("--hours", type=Decimal, default=Decimal(730))
    parser.add_argument("--billable-egress-gb", type=Decimal, default=Decimal(10))
    parser.add_argument("--log-ingest-gb", type=Decimal, default=Decimal(5))
    args = parser.parse_args()
    catalog = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    architectures = ["simple", "managed"] if args.architecture == "both" else [args.architecture]
    print(
        json.dumps(
            [
                estimate(
                    catalog,
                    item,
                    hours=args.hours,
                    billable_egress_gb=args.billable_egress_gb,
                    log_ingest_gb=args.log_ingest_gb,
                )
                for item in architectures
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
