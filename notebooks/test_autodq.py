from autodq import AutoDQ

project = AutoDQ("datasets/sample/sales.csv")


project.set_type("Date", "datetime")
project.set_target("Revenue")
project.profile()
project.show_profile()

project.diagnose()
project.show_diagnosis()

project.recommend()
project.show_recommendations()

project.decide()
project.preview()
project.show_preview()
project.show_session()