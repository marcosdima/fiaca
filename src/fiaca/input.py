from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.styles import Style


_style = Style.from_dict(
    {
        "prompt": "bold ansicyan",
        "bottom-toolbar": "bg:#202020 #aaaaaa",
    }
)


def create_prompt_session() -> PromptSession[str]:
    bindings = KeyBindings()

    @bindings.add("enter")
    def submit(event: KeyPressEvent) -> None:
        event.current_buffer.validate_and_handle()

    @bindings.add("c-s")
    def submit_with_control_s(event: KeyPressEvent) -> None:
        event.current_buffer.validate_and_handle()

    @bindings.add("escape", "enter")
    def insert_newline(event: KeyPressEvent) -> None:
        event.current_buffer.insert_text("\n")

    return PromptSession(
        multiline=True,
        key_bindings=bindings,
        style=_style,
        prompt_continuation="... ",
        bottom_toolbar=(
            "Enter: send  |  Alt-Enter: new line  |  "
            "Ctrl-C: cancel  |  /exit: quit"
        ),
    )


def read_message(session: PromptSession[str]) -> str | None:
    try:
        value = session.prompt("you> ")
    except KeyboardInterrupt:
        return None
    except EOFError:
        return "/exit"
    return value.strip()
