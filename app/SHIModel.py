import logging
from typing import Iterable, Dict, Union, List

import numpy as np
import os
import joblib
import datetime
import json

import requests
from cloudevents.http import CloudEvent, to_json, to_structured

logger = logging.getLogger('SHIModel')


class SHIModel(object):
    result = {}

    def __init__(self):
        self.loaded = False
        self.model = None
        self.sigma = None

    def load(self):
        print("Loading model", os.getpid())
        self.model = joblib.load("./models/model.joblib")
        self.sigma = joblib.load("./models/sigma.joblib")
        self.loaded = True
        print("Loaded model")

    def predict(self,
                X: np.ndarray,
                names: Iterable[str],
                meta: Dict = None) -> Union[np.ndarray, List, str, bytes]:
        if not self.loaded:
            self.load()
        y = X.reshape(-1, 1)
        prediction = np.array(self.model.predict(y)).reshape(-1, 1)
        return prediction

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

    def predict_raw(self, request):
        if not self.loaded:
            self.load()
        print(request)

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

    def tags(self):
        return self.result
