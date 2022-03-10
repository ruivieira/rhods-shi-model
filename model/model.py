import kserve
import logging
from typing import Dict
from xgboost import XGBRegressor
import numpy as np
import json
import datetime
import joblib
from cloudevents.http import CloudEvent, to_json, to_structured
import requests

logger = logging.getLogger("SHIModel")


class SHIModel(kserve.KFModel):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name
        self.model = XGBRegressor()
        self.sigma = None
        self.load()

    def load(self):
        logger.info("Loading model")
        self.sigma = joblib.load("./sigma.joblib")
        self.model.load_model("./model.bst")

    def _diagnosis(self, e):
        if e > 3 * self.sigma:
            return "dangerously high load"
        elif e > 2 * self.sigma:
            return "very high load"
        elif e > self.sigma:
            return "high load"
        elif abs(e) < self.sigma:
            return "normal load"
        else:
            return "low load"

    async def preprocess(self, request: Dict) -> Dict:
        return request

    def predict(self, request: Dict) -> Dict:
        logger.info(request)

        # create a CloudEvent
        # get day number for ISO 8601

        # create a CloudEvent
        # get day number for ISO 8601

        # get attributes
        _time = request.get("time")
        _source = request.get("source")
        _type = request.get("type")
        _obclienturi = request.get("obclienturi")

        # get data
        data = request.get("data")
        _current_load = data.get("currentLoad")
        _host = data.get("host")

        # calculate fields
        _day = datetime.datetime.strptime(_time, "%Y-%m-%dT%H:%M:%S%f%z").timetuple().tm_yday
        _day = np.array(_day).reshape(-1, 1)
        _predicted_load = self.model.predict(_day)
        _estimated_load = np.asscalar(_predicted_load)
        _e = _current_load - _estimated_load
        _diagnosis = self._diagnosis(_e)

        # Create POST CloudEvent object
        post_attributes = {
            "source": _source,
            "type": _type,
            "datacontenttype": "application/json",
        }

        post_data = {
            "host": _host,
            "currentLoad": _current_load,
            "estimatedLoad": _estimated_load,
            "e": _e,
            "diagnosis": _diagnosis
        }

        post_response = CloudEvent(post_attributes, post_data)

        post_headers, post_body = to_structured(post_response)
        post_headers.pop('content-type')
        post_headers['Content-Type'] = "application/json"

        logger.info("Sending POST body %s", str(post_body))
        logger.info("Sending POST headers %s", str(post_headers))
        try:
            logger.info("Sending POST request to %s", _obclienturi)
            requests.post(url=_obclienturi, data=post_body, headers=post_headers)
        except requests.exceptions.RequestException as ex:
            logger.error("Error sending CloudEvent to %s", _obclienturi)
            logger.error(ex)

        # Create this endpoints response CloudEvent object
        response_data = {
            "host": _host,
            "currentLoad": _current_load,
            "estimatedLoad": _estimated_load,
            "e": _e,
            "diagnosis": _diagnosis
        }
        response_event = CloudEvent(post_attributes, response_data)
        return json.loads(to_json(response_event))


if __name__ == "__main__":
    model = SHIModel("rhods-shi-model")
    kserve.KFServer().start([model])
