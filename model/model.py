import kserve
import logging
from typing import Dict
from xgboost import XGBRegressor
import numpy as np


logger = logging.getLogger("SHIModel")


class SHIModel(kserve.KFModel):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name
        self._model = XGBRegressor()
        self.load()

    def load(self):
        logger.info("Loading model")
        self._model.load_model("./model.bst")

    def predict(self, request: Dict) -> Dict:
        logger.info(request)
        data = request.get("data")
        _day = np.array(data).reshape(-1, 1)
        _predicted_load = self._model.predict(_day)
        _estimated_load = np.asscalar(_predicted_load)
        return {"estimatedLoad": _estimated_load}


if __name__ == "__main__":
    model = SHIModel("rhods-shi-model")
    kserve.KFServer().start([model])
