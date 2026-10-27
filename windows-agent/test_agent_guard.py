import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("agent", Path(__file__).with_name("agent.py"))
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

class Handle:
    def __init__(self, field): self.field = field
    async def evaluate(self, script, other): return self.field is other.field
class Field:
    def __init__(self, value): self.value = value
    async def is_visible(self): return True
    async def input_value(self): return self.value
    async def element_handle(self): return Handle(self)
class Controls:
    def __init__(self, field): self.field = field
    async def count(self): return 1
    def nth(self, i): return self.field
class Scope:
    def __init__(self, field): self.field = field
    async def count(self): return 1
    def locator(self, selector): return Controls(self.field)
class Label:
    def __init__(self, field): self.field = field
    async def is_visible(self): return True
    def locator(self, selector): return Scope(self.field)
class Matches:
    def __init__(self, field): self.field = field
    async def count(self): return 1 if self.field else 0
    def nth(self, i): return Label(self.field)
class Button:
    def __init__(self, frame): self.frame = frame
    async def is_visible(self): return True
    async def click(self):
        for field in self.frame.fields.values(): field.value = ""
class Buttons:
    def __init__(self, frame, name): self.frame, self.name = frame, name
    async def count(self): return 1 if self.name == "신규" else 0
    def nth(self, i): return Button(self.frame)
class Frame:
    def __init__(self):
        self.fields = {"회원명": Field("기존 고객"), "휴대폰번호": Field("01012345678")}
    def get_by_text(self, label, exact=False): return Matches(self.fields.get(label))
    def get_by_role(self, role, name, exact=False):
        assert exact
        return Buttons(self, name if role == "button" else "")
    def locator(self, selector): return Buttons(self, "")

async def check():
    frame = Frame()
    old_sleep = agent.asyncio.sleep
    async def no_sleep(*args): return None
    agent.asyncio.sleep = no_sleep
    try:
        try:
            await agent.assert_new_form(frame)
        except RuntimeError:
            pass
        else:
            raise AssertionError("An existing customer was accepted as a new form")
        assert frame.fields["회원명"].value == "기존 고객"
        await agent.click_new(frame)
        await agent.assert_new_form(frame)
        assert frame.fields["회원명"].value == ""
    finally:
        agent.asyncio.sleep = old_sleep

if __name__ == "__main__":
    try:
        check().send(None)
    except StopIteration:
        pass
    print("New-form overwrite guard passed")
