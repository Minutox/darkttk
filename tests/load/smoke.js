import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    steady: {
      executor: "ramping-arrival-rate",
      startRate: 2,
      timeUnit: "1s",
      preAllocatedVUs: 20,
      maxVUs: 100,
      stages: [
        { target: 20, duration: "1m" },
        { target: 20, duration: "3m" },
        { target: 0, duration: "30s" },
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500", "p(99)<1000"],
  },
};

const baseUrl = __ENV.BASE_URL || "http://localhost:8000";

export default function healthJourney() {
  const live = http.get(`${baseUrl}/health/live`);
  check(live, { "liveness 200": (response) => response.status === 200 });
  const ready = http.get(`${baseUrl}/health/ready`);
  check(ready, { "readiness 200": (response) => response.status === 200 });
  sleep(Math.random());
}
