class Connection:
    def __init__(self):
        self.connect_status = "not-connected"


    def update(self, connect_status):
        self.connect_status = connect_status

    def get_status(self):
        return self.connect_status