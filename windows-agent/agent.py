import asyncio, json, os, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Windows consoles and redirected CI output can default to a legacy code page.
# Reconfigure before the first Korean prompt or diagnostic is printed.
for stream in (sys.stdout, sys.stderr):
    if stream is not None and hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

SITE = "https://harehare-member.avionenpapier1.chatgpt.site"
MEMBER_URL = "https://asp.upsolution.co.kr/Customer/Management/100052"
ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

def api(method, path, key, body=None):
    # The membership Site rejects urllib's default Python-urllib user agent.
    # Send the same browser identity used by the existing Windows agent.
    data = None; headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode(); headers["Content-Type"] = "application/json"
    req = Request(SITE + path, headers=headers, method=method, data=data)
    try:
        with urlopen(req, timeout=30) as res: return json.loads(res.read().decode())
    except HTTPError as exc:
        raise RuntimeError(f"관리 서버 오류 HTTP {exc.code}") from exc

async def text(page):
    return (await page.locator("body").inner_text()).lower()

async def visible(page, selector):
    loc = page.locator(selector).first
    try:
        if await loc.is_visible(timeout=500): return loc
    except Exception: pass
    return None

async def click_label(frame, labels, value=None):
    for label in labels:
        row = frame.locator("tr, .row, .form-row, .field, .item").filter(has_text=label).first
        try:
            if not await row.is_visible(timeout=600): continue
            if value:
                control = row.get_by_text(value, exact=True).first
                if await control.is_visible(timeout=500): await control.click(); return True
            control = row.locator("input, textarea, select, button").first
            if await control.is_visible(timeout=500): await control.click(); return True
        except Exception: pass
    return False

async def require_click(frame, labels, value=None):
    if not await click_label(frame, labels, value):
        raise RuntimeError(f"버튼 인식 실패: {labels[0]} {value or ''}")

async def fill_label(frame, labels, value, required=True):
    for label in labels:
        row = frame.locator("tr, .row, .form-row, .field, .item").filter(has_text=label).first
        try:
            control = row.locator("input:not([type=radio]):not([type=checkbox]), textarea").first
            if await control.is_visible(timeout=700):
                await control.fill(str(value or "")); return
        except Exception: pass
    if required: raise RuntimeError(f"필드 인식 실패: {labels[0]}")

async def click_new(frame):
    for selector in ["button", "a", "input[type=button]"]:
        for caption in ["신규", "새로입력", "등록"]:
            loc = frame.locator(selector).filter(has_text=caption).first
            try:
                if await loc.is_visible(timeout=500): await loc.click(); return
            except Exception: pass
    raise RuntimeError("신규 버튼을 찾지 못했습니다.")

async def click_save(frame):
    buttons = frame.locator("button, a, input[type=button]")
    for i in range(await buttons.count()):
        b = buttons.nth(i)
        try:
            if await b.is_visible(timeout=300) and "저장" in (await b.inner_text()).strip():
                await b.click(); return
        except Exception: pass
    raise RuntimeError("저장 버튼을 찾지 못했습니다.")

async def register(frame, member):
    # 1) 기본 탭에서 신규를 먼저 누른다.
    await require_click(frame, ["기본"])
    await click_new(frame)
    await fill_label(frame, ["회원명", "고객명"], member.get("memberName"))
    await fill_label(frame, ["전화번호"], member.get("telephone"), required=False)
    await fill_label(frame, ["휴대폰번호", "휴대전화"], member.get("mobile"))
    if member.get("gender"):
        await require_click(frame, ["성별"], member["gender"])
    # 회원그룹·멤버십카드번호·선수예치금은 건너뜀
    await fill_label(frame, ["우편번호"], member.get("postcode"))
    await fill_label(frame, ["주소"], member.get("address"))
    await fill_label(frame, ["상세주소"], member.get("addressDetail"), required=False)

    # 2) 부가기능
    await require_click(frame, ["부가기능"])
    if member.get("smsAllowed"):
        await require_click(frame, ["SMS 발송"], "예")
        await require_click(frame, ["DM 발송"], "예")
    else:
        await require_click(frame, ["SMS 발송"], "아니오")
        await require_click(frame, ["DM 발송"], "아니오")
    # 메일 발송·결혼기념일·이메일·기존 주소 사용은 건너뜀
    if member.get("birthday"):
        await fill_label(frame, ["생년월일"], member["birthday"])
        await require_click(frame, ["음력"], "예")
    await click_save(frame)
    print("업솔루션 저장 확인창에서 왼쪽 Yes/예를 눌러 주세요.")
    answer = input("업솔루션에서 해당 회원이 실제 등록된 것을 확인했습니까? [y/N]: ").strip().lower()
    if answer != "y":
        raise RuntimeError("저장 결과 미확인: 성공 처리하지 않았습니다. 관리자 화면에서 확인 후 재등록하세요.")

async def main():
    print("Harehare POS Agent v43.1")
    if "--self-test" in sys.argv:
        assert SITE.startswith("https://") and MEMBER_URL.startswith("https://")
        print("SELF-TEST OK: Python 패키징과 설정 검증 완료 (POS 등록 검증은 아님)")
        return
    print("저장 완료 판별을 검증하지 못해 최종 성공 여부는 운영자가 확인합니다.")
    key = input("POS 동기화키: ").strip()
    port = input("브라우저 원격 연결 포트 [9222]: ").strip() or "9222"
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        try: browser = await pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        except Exception as exc:
            print(f"브라우저 연결 실패: {exc}\n브라우저를 원격 디버깅 포트로 실행한 뒤 다시 시도하세요."); return
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = next((p for p in context.pages if "upsolution" in (p.url or "").lower()), None)
        page = page or await context.new_page()
        if "upsolution" not in (page.url or "").lower(): await page.goto(MEMBER_URL, wait_until="domcontentloaded")
        print("로그인된 업솔루션 브라우저를 감시합니다. 종료하려면 Ctrl+C")
        while True:
            try:
                data = api("GET", "/api/sync", key)
            except Exception as exc:
                print(f"동기화 요청 실패: {exc}")
                if "HTTP 401" in str(exc):
                    key = input("POS 동기화키를 다시 입력하세요: ").strip()
                elif "HTTP 403" in str(exc):
                    input("서버가 요청을 차단했습니다. 연결을 확인한 뒤 Enter를 누르면 재시도합니다.")
                else:
                    await asyncio.sleep(15)
                continue
            member = data.get("member")
            if member:
                try:
                    await register(page, member)
                    api("POST", "/api/sync", key, {"id": member["id"], "ok": True, "verified": True})
                    print(f"등록 완료: {member.get('memberName','')}")
                except Exception as exc:
                    api("POST", "/api/sync", key, {"id": member["id"], "ok": False, "error": str(exc)[:240]})
                    print(f"등록 실패 후 다음 고객으로 이동: {exc}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("종료했습니다.")
    except Exception as exc:
        print(f"프로그램 오류: {type(exc).__name__}: {exc}")
        try: input("오류 내용을 확인한 뒤 Enter를 누르면 종료합니다.")
        except EOFError: pass
