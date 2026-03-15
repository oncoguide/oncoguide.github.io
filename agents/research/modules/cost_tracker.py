"""Track API costs across all Claude calls. Enforce budget cap."""

import logging

logger = logging.getLogger(__name__)

# Pricing per million tokens (as of 2025)
PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
}

# Fallback for unknown models
DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


class CostTracker:
    """Track cumulative API cost and enforce a hard budget cap."""

    def __init__(self, max_cost_usd: float = 5.0):
        self.max_cost_usd = max_cost_usd
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.calls: list[dict] = []

    def track(self, model: str, input_tokens: int, output_tokens: int):
        """Record an API call's token usage. Raises RuntimeError if budget exceeded."""
        pricing = PRICING.get(model, DEFAULT_PRICING)
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost
        self.calls.append({"model": model, "input": input_tokens, "output": output_tokens, "cost": cost})

        if self.total_cost_usd > self.max_cost_usd:
            raise RuntimeError(
                f"Budget exceeded: ${self.total_cost_usd:.4f} > ${self.max_cost_usd:.2f}. "
                f"Stopping to prevent runaway costs."
            )

    def has_budget(self, reserve_usd: float = 0.0) -> bool:
        """Check if there's budget remaining (optionally with a reserve)."""
        return self.total_cost_usd + reserve_usd < self.max_cost_usd

    def report(self) -> str:
        """Human-readable cost summary."""
        lines = [f"Total: ${self.total_cost_usd:.4f} / ${self.max_cost_usd:.2f}"]
        lines.append(f"Tokens: {self.total_input_tokens:,} in, {self.total_output_tokens:,} out")
        lines.append(f"API calls: {len(self.calls)}")
        # Breakdown by model
        by_model: dict[str, float] = {}
        for c in self.calls:
            by_model[c["model"]] = by_model.get(c["model"], 0) + c["cost"]
        for model, cost in sorted(by_model.items()):
            lines.append(f"  {model}: ${cost:.4f}")
        return "\n".join(lines)
