import json
import unittest
from decimal import Decimal

from scripts.estimate_aws_costs import SNAPSHOT, estimate


class CostEstimateTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_simple_uses_decimal_math_and_separates_optional_allowances(self):
        result = estimate(self.catalog, "simple")
        self.assertEqual(result["fixed_monthly_usd"], "21.23")
        self.assertEqual(result["example_monthly_usd"], "23.63")
        self.assertTrue(
            all("source_url" in rate and "sku" in rate for rate in self.catalog["rates"].values())
        )

    def test_managed_does_not_double_count_multiaz_rds_but_counts_both_redis_nodes(self):
        result = estimate(self.catalog, "managed")
        rows = {row["rate_key"]: row for row in result["rows"]}
        self.assertEqual(Decimal(rows["rds_micro_multiaz_hour"]["quantity"]), Decimal(730))
        self.assertEqual(Decimal(rows["redis_micro_hour"]["quantity"]), Decimal(730) * 2)
        self.assertEqual(Decimal(rows["public_ipv4_hour"]["quantity"]), Decimal(730) * 3)
        self.assertEqual(Decimal(rows["rds_multiaz_gp3_gb_month"]["quantity"]), Decimal(20))

    def test_invalid_usage_or_region_cannot_produce_a_plausible_quote(self):
        for usage in (-1, Decimal("NaN"), Decimal("Infinity")):
            with self.assertRaises(ValueError):
                estimate(self.catalog, "simple", hours=usage)
        with self.assertRaises(ValueError):
            estimate({**self.catalog, "region": "us-east-1"}, "simple")
