import enum
import queue
import sys
import threading
import time
from socket import AF_INET, SO_REUSEADDR, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, socket


class Event(enum.Enum):
    TICK = 1
    NS_BUTTON = 2
    EW_BUTTON = 3


class LightLogic:
    def __init__(
        self, clock=0, ns_color="R", ew_color="G", ns_button=False, ew_button=False
    ):
        self.clock = clock  # elapsed timer
        self.ns_color = ns_color  # color currently showing in NS dir
        self.ew_color = ew_color
        self.ns_button = ns_button  # ns button being pressed?
        self.ew_button = ew_button

    def __repr__(self):
        return f"LightLogic({self.clock}, {self.ns_color}, {self.ew_color}, {self.ns_button}, {self.ew_button})"

    def invariants(self):
        """check things not supposed to happen"""
        assert self.ns_color != self.ew_color
        assert not (self.ns_color in {"G", "Y"} and self.ew_color in {"G", "Y"})

    # single point of event handling (internal dispatch)
    def handle_event(self, event: Event):
        match event:
            case Event.TICK:
                self.handle_clock_tick()
            case Event.NS_BUTTON:
                self.handle_ns_button()
            case Event.EW_BUTTON:
                self.handle_ew_button()
            case _:
                sys.exit("Unknown event: {event}")
        self.update_colors()
        self.invariants()

    def handle_clock_tick(self):
        self.clock += 1

    def handle_ns_button(self):
        self.ns_button = True

    def handle_ew_button(self):
        self.ew_button = True

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

        self.invariants()


# configuration
EW_LIGHT = ("localhost", 10000)
NS_LIGHT = ("localhost", 11000)
BUTTON = ("localhost", 20000)
TICK_INTERVAL = 0.25


class LightControl:
    def __init__(self):
        self.logic = LightLogic()
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind(BUTTON)
        self.event_queue = queue.Queue()

    def display_colors(self):
        self.sock.sendto(self.logic.ew_color.encode("utf-8"), EW_LIGHT)
        self.sock.sendto(self.logic.ns_color.encode("utf-8"), NS_LIGHT)

    def start(self):
        threading.Thread(target=self.generate_ticks).start()
        threading.Thread(target=self.watch_buttons).start()
        threading.Thread(target=self.event_loop).start()

    def generate_ticks(self):
        while True:
            time.sleep(TICK_INTERVAL)
            self.event_queue.put(Event.TICK)

    def watch_buttons(self):
        while True:
            msg, addr = self.sock.recvfrom(100)
            if b"EW" in msg:
                self.event_queue.put(Event.EW_BUTTON)
            elif b"NS" in msg:
                self.event_queue.put(Event.NS_BUTTON)

    def event_loop(self):
        while True:
            print(self.logic)  # debug
            event = self.event_queue.get()
            self.logic.handle_event(event)
            self.display_colors()

    def run(self):
        # timer
        while True:
            # time elapse
            time.sleep(1)
            self.logic.handle_clock_tick()

            self.logic.update_colors()
            self.display_colors()


if __name__ == "__main__":
    control = LightControl()
    control.start()
