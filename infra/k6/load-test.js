import { check, group, sleep } from "k6";
import http from "k6/http";
import { Trend } from "k6/metrics";

/*
 * RailFlow load profile.
 *
 * Run against the local stack:
 *   k6 run infra/k6/load-test.js
 *   BASE_URL=http://demo.localhost:8095 k6 run infra/k6/load-test.js
 *
 * Scenarios are selected with SCENARIO: smoke | load | stress (default load).
 */

const BASE_URL = __ENV.BASE_URL || "http://demo.localhost:8095";
const SLUG = __ENV.TENANT_SLUG || "demo";
const EMAIL = __ENV.EMAIL || "demo@railway.demo";
const PASSWORD = __ENV.PASSWORD || "demo1234";
const SCENARIO = __ENV.SCENARIO || "load";

const bookingLatency = new Trend("booking_create_latency", true);

const scenarios = {
  smoke: {
    executor: "constant-vus",
    vus: 1,
    duration: "30s",
  },
  load: {
    executor: "ramping-vus",
    startVUs: 1,
    stages: [
      { duration: "30s", target: 10 },
      { duration: "1m", target: 20 },
      { duration: "30s", target: 0 },
    ],
  },
  stress: {
    executor: "ramping-vus",
    startVUs: 5,
    stages: [
      { duration: "30s", target: 25 },
      { duration: "1m", target: 50 },
      { duration: "30s", target: 0 },
    ],
  },
};

export const options = {
  scenarios: { [SCENARIO]: scenarios[SCENARIO] },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

export function setup() {
  const headers = { "Content-Type": "application/json" };
  const payload = JSON.stringify({ tenant_slug: SLUG, email: EMAIL, password: PASSWORD });
  const response = http.post(`${BASE_URL}/api/v1/auth/login`, payload, { headers });
  if (response.status !== 200) {
    throw new Error(`setup login failed: ${response.status} ${response.body}`);
  }
  const body = response.json();

  const trains = http
    .get(`${BASE_URL}/api/v1/trains?page_size=5`, {
      headers: { Authorization: `Bearer ${body.access_token}` },
    })
    .json();

  return {
    token: body.access_token,
    trainId: trains.items[0].id,
  };
}

export default function (data) {
  const auth = { Authorization: `Bearer ${data.token}` };

  group("browse", () => {
    const overview = http.get(`${BASE_URL}/api/v1/reports/overview`, { headers: auth });
    check(overview, { "overview 200": (r) => r.status === 200 });

    const trains = http.get(`${BASE_URL}/api/v1/trains?page_size=20`, { headers: auth });
    check(trains, { "trains 200": (r) => r.status === 200 });

    const bookings = http.get(`${BASE_URL}/api/v1/bookings?page_size=20`, { headers: auth });
    check(bookings, { "bookings 200": (r) => r.status === 200 });
  });

  group("booking", () => {
    const payload = JSON.stringify({
      train_id: data.trainId,
      travel_date: new Date(Date.now() + 14 * 24 * 3600 * 1000).toISOString().slice(0, 10),
      contact_name: `Load Test ${__VU}`,
      contact_email: `load-${__VU}-${__ITER}@example.com`,
      contact_phone: "+1-555-0100",
      seats: 1,
      passengers: [{ full_name: `Load Test ${__VU}`, age: 30 }],
      channel: "online",
    });
    const response = http.post(`${BASE_URL}/api/v1/bookings`, payload, {
      headers: { ...auth, "Content-Type": "application/json" },
    });
    bookingLatency.add(response.timings.duration);
    check(response, {
      "booking created or seats exhausted": (r) => r.status === 201 || r.status === 409,
    });
  });

  sleep(1);
}
