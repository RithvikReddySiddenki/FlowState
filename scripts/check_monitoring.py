"""Read-only checks for the isolated synthetic monitoring stack."""

import os

import httpx


def main():
    password = os.environ["GRAFANA_ADMIN_PASSWORD"]
    with httpx.Client(timeout=15) as client:
        response = client.get("http://localhost:19090/api/v1/targets")
        response.raise_for_status()
        targets = response.json()["data"]["activeTargets"]
        expected = {"flowstate-api", "flowstate-operations"}
        assert expected <= {item["labels"]["job"] for item in targets}
        assert all(item["health"] == "up" for item in targets)
        for metric in ("flowstate_database_available", "flowstate_broker_available"):
            response = client.get("http://localhost:19090/api/v1/query", params={"query": metric})
            response.raise_for_status()
            values = response.json()["data"]["result"]
            assert values and all(float(item["value"][1]) == 1 for item in values)
        response = client.get("http://localhost:13001/api/search", auth=("admin", password))
        response.raise_for_status()
        assert any(item["title"] == "FlowState operations" for item in response.json())
    print("Private scrape targets, dependency gauges and provisioned dashboard passed")


if __name__ == "__main__":
    main()
