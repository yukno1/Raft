import queue
import time
from socket import AF_INET, SO_REUSEADDR, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, socket

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

    def handle_clock_tick(self):
        self.clock += 1
        self.update_colors()

    # method takes care of all states
    def update_colors(self):
        # ew light stays green for 30s
        if self.ew_color == "G" and self.ns_color == "R":
            if self.clock >= 30 or (self.clock >= 15 and self.ns_button):
                self.ew_color = "Y"
                self.clock = 0
                self.ns_button = False

        # ns light stays green for 60s
        elif self.ew_color == "R" and self.ns_color == "G":
            if self.clock >= 60 or (self.clock >= 15 and self.ew_button):
                self.ns_color = "Y"
                self.clock = 0
                self.ew_button = False

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


# configuration
EW_LIGHT = ("localhost", 10000)
NS_LIGHT = ("localhost", 11000)
BUTTON = ("localhost", 20000)


class LightControl:
    def __init__(self):
        self.logic = LightLogic()
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.bind(BUTTON)
        self.event_queue = queue.Queue()

    def display_colors(self):
        self.sock.sendto(self.logic.ew_color.encode("utf-8"), EW_LIGHT)
        self.sock.sendto(self.logic.ns_color.encode("utf-8"), NS_LIGHT)

    def event_loop(self):
        while True:
            event = self.event_queue.get()
            self.logic.handle_event(event)  # TODO
            self.display_colors()

    def run(self):
        # timer
        while True:
            # time elapse
            time.sleep(1)
            self.logic.handle_clock_tick()

            self.logic.update_colors()
            self.display_colors()
