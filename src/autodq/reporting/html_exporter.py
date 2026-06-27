class HTMLExporter:

    def export(self, report, path):

        html = f"""

<html>

<head>

<title>AutoDQ Report</title>

</head>

<body>

<h1>AutoDQ Analytics Report</h1>

<hr>

<h2>Dataset</h2>

<p>{report.dataset}</p>

<h2>Quality Score</h2>

<p>{report.validation.quality_score_before}
→
{report.validation.quality_score_after}

</p>

<h2>Generated</h2>

<p>{report.generated_at}</p>

</body>

</html>

"""

        with open(path,"w") as f:

            f.write(html)