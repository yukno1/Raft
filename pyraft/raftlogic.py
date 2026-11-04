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


class RaftLogic:
    def __init__(self, nodenum):
        self.nodenum = nodenum

    def handle_msg(self, msg: Message):
        if isinstance(msg, ChatMessage):
            self.handle_chat_msg(msg)
        else:
            raise TypeError(f"Can't handle {msg}")

    def handle_chat_msg(self, msg: ChatMessage):
        print(f"{msg.sender} said {msg.text}")
        # what message to send back
