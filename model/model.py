import kserve

from typing import Dict


class SHIModel(kserve.KFModel):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name
        self.load()

    def load(self):
        pass

    def predict(self, request: Dict) -> Dict:
        print(request)
        return {"result": 42}


if __name__ == "__main__":
    model = SHIModel("rhods-shi-model")
    kserve.KFServer().start([model])
