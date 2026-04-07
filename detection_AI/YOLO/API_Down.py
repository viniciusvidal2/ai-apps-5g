
import roboflow

rf = roboflow.Roboflow(api_key="mYNkfy6QOq4vGnLEeGCn")
model = rf.workspace().project("find-people-helmets-glasses-vests-gloves-masks-ear-protectors-and-boots").version("1").model
model.download() # Downloads 'weights.pt' to your local folder