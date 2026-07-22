import json
from datetime import date, datetime
from pathlib import Path

import numpy as np


class JSONExporter:

    def export(self, report, path):

        payload = {

            "dataset": report.dataset,

            "profile": report.profile,

            "statistics":
                report.statistics.to_dict()
                if report.statistics else None,

            "interpretations":
                report.interpretations.to_dict()
                if report.interpretations else None,

            "diagnosis":
                report.diagnosis.to_dict()
                if report.diagnosis else None,

            "recommendations":[
                r.to_dict()
                for r in report.recommendations
            ] if report.recommendations else None,

            "decision_plan":
                report.decision_plan.to_dict()
                if report.decision_plan else None,

            "preview":
                report.preview.to_dict()
                if report.preview else None,

            "cleaning":
                report.cleaning.to_dict()
                if report.cleaning else None,

            "cleaning_review":
                report.cleaning_review.to_dict()
                if report.cleaning_review else None,

            "domain_validation":
                report.domain_validation.to_dict()
                if report.domain_validation else None,

            "automation":
                report.automation.to_dict()
                if report.automation else None,

            "dashboard":
                report.dashboard.to_dict()
                if report.dashboard else None,

            "adql_history": [
                run.to_dict()
                for run in (report.adql_history or [])
            ],

            "validation":
                report.validation.to_dict()
                if report.validation else None,
                
            "visualizations":
                report.visualizations.to_dict()
                if report.visualizations else None,

            "generated_at":
                report.generated_at.isoformat()

        }

        with open(path,"w") as f:

            json.dump(
                payload,
                f,
                indent=4,
                default=self._json_default,
            )

    @staticmethod
    def _json_default(value):
        if isinstance(value, np.generic):
            return value.item()

        if isinstance(value, (datetime, date, Path)):
            return str(value)

        if hasattr(value, "to_dict"):
            return value.to_dict()

        raise TypeError(
            f"Object of type {type(value).__name__} is not JSON serializable"
        )
