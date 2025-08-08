"""Production Performance System"""

import functools
import time


class PerformanceProfiler:
    """Performance profiler for all components"""

    def __init__(self):
        self.profiles = {}

    def profile(self, component_name, method_name):
        """Profile component method"""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    result = None
                    success = False
                    raise
                finally:
                    duration = time.perf_counter() - start_time
                    profile_key = f"{component_name}.{method_name}"

                    if profile_key not in self.profiles:
                        self.profiles[profile_key] = []

                    self.profiles[profile_key].append({"duration": duration, "success": success})

                return result

            return wrapper

        return decorator

    def get_report(self):
        """Get performance report"""
        report = {}
        for profile_key, calls in self.profiles.items():
            if calls:
                avg_duration = sum(call["duration"] for call in calls) / len(calls)
                success_rate = sum(1 for call in calls if call["success"]) / len(calls)

                report[profile_key] = {
                    "total_calls": len(calls),
                    "avg_duration": avg_duration,
                    "success_rate": success_rate,
                }

        return report


profiler = PerformanceProfiler()
