import json


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

            json.dump(payload,f,indent=4)