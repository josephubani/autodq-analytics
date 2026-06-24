from autodq import AutoDQ
import os
print("Current Working Directory:", os.getcwd())

project = AutoDQ("datasets/sample/sales.csv")
project.profile()
project.show_profile()