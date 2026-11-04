from dataclasses import dataclass


@dataclass
class Message:
    dest: int


# debug
@dataclass
class ChatMessage(Message):
    sender: int
    text: str

    def __repr__(self):
        return f"{self.sender} said {self.text}"


# Response sent to ack chat message
@dataclass
class ChatResponse(Message):
    sender: int
    orig_text: str

    def __repr__(self):
        return f"{self.sender} got {self.orig_text}"


@dataclass
class AppendEntries(Message): ...


class RaftLogic:
    def __init__(self, nodenum):
        self.nodenum = nodenum
        self.curr_term = None
        self.commit_index = None

        # internal messageing
        self._outgoing = []

    # implement instanal messaging for logic
    def send(self, msg):
        self._outgoing.append(msg)

    def handle_msg(self, msg: Message) -> list[Message]:
        """Dispatch messages"""
        self._outgoing = []
        if isinstance(msg, ChatMessage):
            self.handle_chat_msg(msg)
        elif isinstance(msg, ChatResponse):
            self.handle_chat_resp(msg)
        else:
            raise TypeError(f"Can't handle {msg}")

    def handle_chat_msg(self, msg: ChatMessage) -> Message:
        print(msg)
        self.send(ChatResponse(msg.sender, self.nodenum, msg.text))
        # what message to send back
        # send(ChatMessage(msg.sender))
        # ^^^^
        # how does send work? because in different object, need net dependency in logic

    def handle_chat_resp(self, msg: ChatResponse):
        """print out ack"""
        print(msg)

    def handle_append_entries(self, msg: AppendEntries): ...


def test_chat():
    logic = RaftLogic(1)
    resp = logic.handle_msg(ChatMessage(1, 2, "hi"))
    assert resp == [ChatResponse(2, 1, "hi")]


if __name__ == "__main__":
    test_chat()
