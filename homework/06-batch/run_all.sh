#!/usr/bin/env bash
set -e

echo "Running Q1..."
uv run python scripts/q1_version.py

echo "Running Q2..."
uv run python scripts/q2_repartition.py

echo "Running Q3..."
uv run python scripts/q3_count_2025_11_15.py

echo "Running Q4..."
uv run python scripts/q4_longest_trip.py

echo "Q5: Spark UI info in scripts/q5_spark_ui.md"

echo "Running Q6..."
uv run python scripts/q6_least_zone.py

echo "Done."