class ConsoleStatisticsRenderer:

    @staticmethod
    def render(report):
        print("\n=== AutoDQ Statistics ===\n")

        for stats in report.descriptive.values():
            print(f"{stats.column}")
            print(f"  Mean: {stats.mean}")
            print(f"  Median: {stats.median}")
            print(f"  Std: {stats.std}")
            print(f"  Skewness: {stats.skewness}")
            print(f"  Kurtosis: {stats.kurtosis}")
            print(f"  Missing: {stats.missing}")

            distribution = report.distributions.get(stats.column)

            if distribution:
                print(f"  Distribution: {distribution.distribution_type}")
                print(f"  Skewness Level: {distribution.skewness_level}")
                print(f"  Tail Risk: {distribution.tail_risk}")
                print(f"  Confidence: {round(distribution.confidence * 100, 2)}%")
                print(f"  Explanation: {distribution.explanation}")

            print()