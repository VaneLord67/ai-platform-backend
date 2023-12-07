import json


class Config:

    def __init__(self):
        with open("config.json", "r") as f:
            self.config = json.load(f)

    def get(self, query):
        return self.config.get(query)


config = Config()
