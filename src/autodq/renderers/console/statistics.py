class ConsoleStatisticsRenderer:

    @staticmethod
    def render(report):

        print("\n=== AutoDQ Statistics ===")

        print()

        for stats in report.descriptive.values():

            print(f"{stats.column}")

            print(f"  Mean: {stats.mean}")

            print(f"  Median: {stats.median}")

            print(f"  Std: {stats.std}")

            print(f"  Skewness: {stats.skewness}")

            print(f"  Kurtosis: {stats.kurtosis}")

            print(f"  Missing: {stats.missing}")

            print()