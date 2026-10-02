import customtkinter as ctk


class FlowApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FLOW | Traffic Signal Timing Optimizer")
        self.geometry("1120x720")
        self.minsize(960, 640)
