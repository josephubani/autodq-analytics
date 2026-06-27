from autodq import AutoDQ

project = AutoDQ("datasets/sample/sales.csv")


project.set_type("Date", "datetime")
project.set_target("Revenue")

project.apply_knowledge()
project.show_knowledge()

project.profile()
project.show_profile()

project.statistics()
project.show_statistics()

project.interpret()
project.show_interpretations()

project.diagnose()
project.show_diagnosis()

project.recommend()
project.show_recommendations()

project.decide()
project.preview()
project.show_preview()

project.approve_all()
project.clean()
project.show_cleaning_report()

project.validate_cleaning()
project.show_validation()

project.visualize( chart = "auto")




project.generate_report("reports/autodq_executive.html", style="executive")
project.generate_report("reports/autodq_dark.html", style="dark")
project.generate_report("reports/autodq_print.html", style="print")

project.show_session()

