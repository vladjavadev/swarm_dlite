class PathObservation:
    def __init__(self):
        self.is_updated = False
        self.next_pos = None
        self.is_done = False

    def update(self, new_next_pos):
        self.next_pos = new_next_pos
        self.is_updated = True