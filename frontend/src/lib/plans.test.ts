import { describe, expect, it } from "vitest";

import {
  FALLBACK_PLANS,
  FEATURE_LABELS,
  QUOTA_LABELS,
  planPrice,
  quotaLabel,
} from "@/lib/plans";

describe("quotaLabel", () => {
  it("renders unlimited, numeric and missing values", () => {
    expect(quotaLabel(-1)).toBe("Unlimited");
    expect(quotaLabel(12)).toBe("12");
    expect(quotaLabel(0)).toBe("0");
    expect(quotaLabel(undefined)).toBe("—");
  });
});

describe("planPrice", () => {
  it("marks free plans", () => {
    expect(planPrice(FALLBACK_PLANS[0])).toBe("Free");
  });

  it("formats monthly prices without cents", () => {
    expect(planPrice(FALLBACK_PLANS[1])).toBe("$49/mo");
    expect(planPrice(FALLBACK_PLANS[2])).toBe("$249/mo");
  });
});

describe("fallback catalog", () => {
  it("mirrors the backend tier structure", () => {
    expect(FALLBACK_PLANS.map((plan) => plan.code)).toEqual(["starter", "growth", "enterprise"]);
    expect(FALLBACK_PLANS.map((plan) => plan.sort_order)).toEqual([0, 1, 2]);
    expect(FALLBACK_PLANS[0].quotas.max_trains).toBe(10);
    expect(FALLBACK_PLANS[2].quotas.max_trains).toBe(-1);
    expect(FALLBACK_PLANS[1].features["reports.advanced"]).toBe(true);
    expect(FALLBACK_PLANS[0].features["reports.advanced"]).toBe(false);
  });

  it("exposes labels for every feature and quota shown in the UI", () => {
    for (const plan of FALLBACK_PLANS) {
      for (const feature of Object.keys(plan.features)) {
        expect(FEATURE_LABELS[feature], feature).toBeTruthy();
      }
      for (const quota of Object.keys(plan.quotas)) {
        expect(QUOTA_LABELS[quota], quota).toBeTruthy();
      }
    }
  });
});
