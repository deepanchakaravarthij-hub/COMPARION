from __future__ import annotations

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import fitz  # type: ignore[import-untyped]
import httpx


def build_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = bytes(document.tobytes())
    document.close()
    return content


def run_compare(base_url: str, index: int, timeout: float) -> dict[str, Any]:
    files = {
        "file_a": ("a.pdf", build_pdf_bytes(f"contract base {index}"), "application/pdf"),
        "file_b": ("b.pdf", build_pdf_bytes(f"contract delta {index}"), "application/pdf"),
    }
    started = time.perf_counter()
    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{base_url}/v1/compare", files=files)
        response.raise_for_status()
        job_id = response.json()["job_id"]
        for _ in range(120):
            status = client.get(f"{base_url}/v1/jobs/{job_id}").json()["status"]
            if status in {"completed", "failed"}:
                break
            time.sleep(0.25)
        result = client.get(f"{base_url}/v1/jobs/{job_id}/result")
        result.raise_for_status()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {"job_id": job_id, "elapsed_ms": elapsed_ms, "status": status}


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple load test for COMPARION compare workflow")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    results = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(run_compare, args.base_url, index, args.timeout)
            for index in range(args.requests)
        ]
        for future in as_completed(futures):
            results.append(future.result())
    total_ms = (time.perf_counter() - started) * 1000

    latencies = [result["elapsed_ms"] for result in results]
    failed = [result for result in results if result["status"] != "completed"]
    print("Load test summary")
    print(f"total_requests={args.requests}")
    print(f"concurrency={args.concurrency}")
    print(f"total_time_ms={round(total_ms, 2)}")
    print(f"avg_latency_ms={round(statistics.mean(latencies), 2)}")
    p95 = statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 2 else latencies[0]
    print(f"p95_latency_ms={round(p95, 2)}")
    print(f"max_latency_ms={round(max(latencies), 2)}")
    print(f"failed_jobs={len(failed)}")


if __name__ == "__main__":
    main()
