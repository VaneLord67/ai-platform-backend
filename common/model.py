import flask


class User:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def __json__(self):
        return {
            "username": self.username,
            "password": self.password,
        }

    @classmethod
    def from_json(cls, data):
        return cls(username=data.get('username'), password=data.get('password'))
