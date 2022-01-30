from flask import Flask, jsonify, request
from SHIModel import SHIModel

application = Flask(__name__)

model = SHIModel()


@application.route("/")
@application.route("/status")
def status():
    return jsonify({"status": "ok"})


@application.route("/predict", methods=["POST"])
def create_prediction():
    prediction = model.predict_raw(request)

    return prediction
