import kserve
import logging
from typing import Dict
from xgboost import XGBRegressor
import numpy as np
import json
import datetime
import joblib
from cloudevents.http import CloudEvent, to_json

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

    def predict(self, request: Dict) -> Dict:
        logger.info(request)

        # create a CloudEvent
        # get day number for ISO 8601

        # get attributes
        _time = request["time"]
        _source = request["source"]
        _type = request["type"]

        # get data
        _current_load = request["currentLoad"]
        _host = request["host"]

        # calculate fields
        _day = (
            datetime.datetime.strptime(_time, "%Y-%m-%dT%H:%M:%S%f%z")
            .timetuple()
            .tm_yday
        )
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

        # Create this endpoints response CloudEvent object
        response_data = {
            "host": _host,
            "currentLoad": _current_load,
            "estimatedLoad": _estimated_load,
            "e": _e,
            "diagnosis": _diagnosis,
        }
        response_event = CloudEvent(post_attributes, response_data)
        return json.loads(to_json(response_event))


if __name__ == "__main__":
    model = SHIModel("rhods-shi-model")
    kserve.KFServer().start([model])
