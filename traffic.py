# implement algorithm as a stand-alone code


class LightLogic:
    def __init__(self):
        self.clock = 0  # elapsed timer
        self.ns_color = "R"  # color currently showing in NS dir
        self.ew_color = "G"
        self.ns_button = False  # ns button being pressed?
        self.ew_button = False

    def __repr__(self):
        return f"LightLogic({self.clock}, {self.ns_color}, {self.ew_color}, {self.ns_button}, {self.ew_button})"

    # method takes care of all states
    def update_colors(self):
        # ew light stays green for 30s
        if self.ew_color == "G" and self.ns_color == "R":
            if self.clock >= 30 or (self.clock >= 15 and self.ns_button):
                self.ew_color = "Y"
                self.clock = 0
        # ns light stays green for 60s
        elif self.ew_color == "R" and self.ns_color == "G":
            if self.clock >= 60 or (self.clock >= 15 and self.ew_button):
                self.ns_color = "Y"
                self.clock = 0
        # yellow light last 5s
        elif self.ew_color == "Y" and self.ns_color == "R":
            if self.clock >= 5:
                self.ns_color = "G"
                self.ew_color = "R"
                self.clock = 0
        elif self.ew_color == "R" and self.ns_color == "Y":
            if self.clock >= 5:
                self.ns_color = "R"
                self.ew_color = "G"
                self.clock = 0
