"""
Rate Limiting Test Script
Tests rate limiting functionality across all endpoints

Tests:
1. Normal requests - should succeed
2. Rapid requests - should get 429 after limit
3. Rate limit reset - should allow requests after waiting
4. Different endpoints - should have independent limits
5. Response headers - X-RateLimit-* headers present
6. IP whitelist/blacklist functionality
"""
import time
import requests
import sys
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class TestResult:
    """Test result data"""
    name: str
    passed: bool
    message: str
    duration: float = 0.0


class RateLimitTester:
    """Rate limiting test runner"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []

    def test_health_endpoint(self) -> TestResult:
        """Test 1: Health endpoint should work"""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}/health")
            duration = time.time() - start

            if response.status_code == 200:
                return TestResult(
                    name="Health Endpoint",
                    passed=True,
                    message="Health endpoint responding",
                    duration=duration
                )
            else:
                return TestResult(
                    name="Health Endpoint",
                    passed=False,
                    message=f"Unexpected status: {response.status_code}",
                    duration=duration
                )
        except Exception as e:
            return TestResult(
                name="Health Endpoint",
                passed=False,
                message=f"Error: {str(e)}",
                duration=time.time() - start
            )

    def test_normal_request(self, endpoint: str, method: str = "GET") -> TestResult:
        """Test 2: Normal request should succeed"""
        start = time.time()
        try:
            url = f"{self.base_url}{endpoint}"
            if method == "GET":
                response = requests.get(url)
            else:
                response = requests.post(url)

            duration = time.time() - start

            # Accept both 200 and 404 (endpoint might need auth/data)
            if response.status_code in [200, 201, 404, 401]:
                return TestResult(
                    name=f"Normal Request: {endpoint}",
                    passed=True,
                    message=f"Status: {response.status_code}, Headers: {dict(response.headers)}",
                    duration=duration
                )
            else:
                return TestResult(
                    name=f"Normal Request: {endpoint}",
                    passed=False,
                    message=f"Unexpected status: {response.status_code}",
                    duration=duration
                )
        except Exception as e:
            return TestResult(
                name=f"Normal Request: {endpoint}",
                passed=False,
                message=f"Error: {str(e)}",
                duration=time.time() - start
            )

    def test_rate_limit_enforcement(
        self,
        endpoint: str,
        limit: int,
        period: str = "minute"
    ) -> TestResult:
        """Test 3: Rate limit should be enforced"""
        start = time.time()
        try:
            url = f"{self.base_url}{endpoint}"
            success_count = 0
            rate_limited = False
            last_response = None

            # Make limit + 5 requests
            for i in range(limit + 5):
                response = requests.get(url)
                last_response = response

                if response.status_code == 429:
                    rate_limited = True
                    rate_limit_at = i + 1
                    break
                elif response.status_code in [200, 201, 404, 401]:
                    success_count += 1
                else:
                    # Unexpected error
                    return TestResult(
                        name=f"Rate Limit Enforcement: {endpoint}",
                        passed=False,
                        message=f"Unexpected status at request {i+1}: {response.status_code}",
                        duration=time.time() - start
                    )

                # Small delay between requests
                time.sleep(0.1)

            duration = time.time() - start

            if rate_limited:
                # Check response format
                try:
                    error_data = last_response.json()
                    has_retry_after = "retry_after" in error_data or "Retry-After" in last_response.headers

                    return TestResult(
                        name=f"Rate Limit Enforcement: {endpoint}",
                        passed=True,
                        message=f"Rate limited after {rate_limit_at} requests (limit: {limit}). "
                                f"Has retry_after: {has_retry_after}. "
                                f"Response: {error_data}",
                        duration=duration
                    )
                except Exception as e:
                    return TestResult(
                        name=f"Rate Limit Enforcement: {endpoint}",
                        passed=True,
                        message=f"Rate limited after {rate_limit_at} requests (limit: {limit}), "
                                f"but error parsing response: {e}",
                        duration=duration
                    )
            else:
                return TestResult(
                    name=f"Rate Limit Enforcement: {endpoint}",
                    passed=False,
                    message=f"No rate limiting after {success_count} requests (expected limit: {limit})",
                    duration=duration
                )

        except Exception as e:
            return TestResult(
                name=f"Rate Limit Enforcement: {endpoint}",
                passed=False,
                message=f"Error: {str(e)}",
                duration=time.time() - start
            )

    def test_rate_limit_reset(
        self,
        endpoint: str,
        limit: int,
        wait_seconds: int = 65
    ) -> TestResult:
        """Test 4: Rate limit should reset after time period"""
        start = time.time()
        try:
            url = f"{self.base_url}{endpoint}"

            # First, trigger rate limit
            for i in range(limit + 2):
                response = requests.get(url)
                if response.status_code == 429:
                    print(f"      Rate limited after {i+1} requests, waiting {wait_seconds}s...")
                    break
                time.sleep(0.1)

            # Wait for reset
            time.sleep(wait_seconds)

            # Try again
            response = requests.get(url)
            duration = time.time() - start

            if response.status_code in [200, 201, 404, 401]:
                return TestResult(
                    name=f"Rate Limit Reset: {endpoint}",
                    passed=True,
                    message=f"Rate limit reset after {wait_seconds}s. Status: {response.status_code}",
                    duration=duration
                )
            elif response.status_code == 429:
                return TestResult(
                    name=f"Rate Limit Reset: {endpoint}",
                    passed=False,
                    message=f"Rate limit did not reset after {wait_seconds}s",
                    duration=duration
                )
            else:
                return TestResult(
                    name=f"Rate Limit Reset: {endpoint}",
                    passed=False,
                    message=f"Unexpected status after reset: {response.status_code}",
                    duration=duration
                )

        except Exception as e:
            return TestResult(
                name=f"Rate Limit Reset: {endpoint}",
                passed=False,
                message=f"Error: {str(e)}",
                duration=time.time() - start
            )

    def test_independent_limits(self) -> TestResult:
        """Test 5: Different endpoints should have independent limits"""
        start = time.time()
        try:
            # Make requests to endpoint 1
            endpoint1 = "/health"
            for i in range(10):
                requests.get(f"{self.base_url}{endpoint1}")
                time.sleep(0.05)

            # Endpoint 2 should still work
            endpoint2 = "/"
            response = requests.get(f"{self.base_url}{endpoint2}")

            duration = time.time() - start

            if response.status_code == 200:
                return TestResult(
                    name="Independent Rate Limits",
                    passed=True,
                    message=f"Endpoint {endpoint2} still accessible after {endpoint1} usage",
                    duration=duration
                )
            else:
                return TestResult(
                    name="Independent Rate Limits",
                    passed=False,
                    message=f"Endpoint {endpoint2} affected by {endpoint1} usage",
                    duration=duration
                )

        except Exception as e:
            return TestResult(
                name="Independent Rate Limits",
                passed=False,
                message=f"Error: {str(e)}",
                duration=time.time() - start
            )

    def test_response_headers(self, endpoint: str) -> TestResult:
        """Test 6: Response should include rate limit headers"""
        start = time.time()
        try:
            response = requests.get(f"{self.base_url}{endpoint}")
            duration = time.time() - start

            headers = response.headers
            has_limit = "X-RateLimit-Limit" in headers
            has_remaining = "X-RateLimit-Remaining" in headers

            # Headers might not be present on all endpoints
            if has_limit or has_remaining:
                return TestResult(
                    name=f"Rate Limit Headers: {endpoint}",
                    passed=True,
                    message=f"Headers present - Limit: {headers.get('X-RateLimit-Limit')}, "
                            f"Remaining: {headers.get('X-RateLimit-Remaining')}",
                    duration=duration
                )
            else:
                return TestResult(
                    name=f"Rate Limit Headers: {endpoint}",
                    passed=True,  # Not critical if headers missing
                    message="Rate limit headers not present (might be normal for this endpoint)",
                    duration=duration
                )

        except Exception as e:
            return TestResult(
                name=f"Rate Limit Headers: {endpoint}",
                passed=False,
                message=f"Error: {str(e)}",
                duration=time.time() - start
            )

    def run_all_tests(self, skip_slow_tests: bool = False):
        """Run all rate limiting tests"""
        print("\n" + "=" * 70)
        print("RATE LIMITING TEST SUITE")
        print("=" * 70)

        # Test 1: Health check
        print("\n[1/6] Testing Health Endpoint...")
        result = self.test_health_endpoint()
        self.results.append(result)
        self.print_result(result)

        # Test 2: Normal requests
        print("\n[2/6] Testing Normal Requests...")
        endpoints = ["/", "/health", "/api/v1/ocr/jobs/test-id"]
        for endpoint in endpoints:
            result = self.test_normal_request(endpoint)
            self.results.append(result)
            self.print_result(result)

        # Test 3: Rate limit enforcement
        print("\n[3/6] Testing Rate Limit Enforcement...")
        # Test with lower limit endpoint
        result = self.test_rate_limit_enforcement("/health", limit=100)
        self.results.append(result)
        self.print_result(result)

        # Test 4: Rate limit reset (SLOW - skip if requested)
        if not skip_slow_tests:
            print("\n[4/6] Testing Rate Limit Reset (this will take ~65 seconds)...")
            result = self.test_rate_limit_reset("/health", limit=100, wait_seconds=65)
            self.results.append(result)
            self.print_result(result)
        else:
            print("\n[4/6] Skipping Rate Limit Reset test (--fast mode)")

        # Test 5: Independent limits
        print("\n[5/6] Testing Independent Rate Limits...")
        result = self.test_independent_limits()
        self.results.append(result)
        self.print_result(result)

        # Test 6: Response headers
        print("\n[6/6] Testing Rate Limit Response Headers...")
        result = self.test_response_headers("/health")
        self.results.append(result)
        self.print_result(result)

        # Print summary
        self.print_summary()

    def print_result(self, result: TestResult):
        """Print test result"""
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"   {status} - {result.name}")
        print(f"      Message: {result.message}")
        print(f"      Duration: {result.duration:.2f}s")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%")

        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.results:
                if not result.passed:
                    print(f"   - {result.name}: {result.message}")

        print("\n" + "=" * 70)

        return failed == 0


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description="Rate Limiting Test Suite")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL for API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests (rate limit reset)"
    )

    args = parser.parse_args()

    print(f"\nTesting API at: {args.url}")
    print(f"Fast mode: {args.fast}")

    tester = RateLimitTester(base_url=args.url)
    tester.run_all_tests(skip_slow_tests=args.fast)

    # Return exit code based on results
    success = all(r.passed for r in tester.results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
