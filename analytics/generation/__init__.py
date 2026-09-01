"""Admin test-data generator.

Split by responsibility so each piece stays testable on its own:

* :mod:`config`        — the settings an administrator submits, validated and normalised.
* :mod:`distributions` — the weighted/seasonal random helpers that make the data look real.
* :mod:`reference`     — the fixed vocabulary (markets, carriers, devices, channels) shared by both builders.
* :mod:`users`         — synthetic customers and their CRM history.
* :mod:`orders`        — orders, items, payments, refunds, returns, shipments, events, subscriptions.
* :mod:`service`       — orchestration, batching, progress reporting.
* :mod:`cleanup`       — deletes exactly what a batch created and nothing else.
"""
from .config import GeneratorConfig
from .service import TestDataGeneratorService
from .cleanup import count_test_data, delete_test_data

__all__ = ["GeneratorConfig", "TestDataGeneratorService", "count_test_data", "delete_test_data"]
