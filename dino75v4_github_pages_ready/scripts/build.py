
#!/usr/bin/env python3
"""Dino75 V4 한국어 GitHub Pages 빌드 스크립트."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlsplit, unquote

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


ORIGIN = "https://dino75v4.xiaojiu99.top/"
HOST = urlsplit(ORIGIN).hostname
MAX_BYTES = 25 * 1024 * 1024
MAX_RESOURCES = 900


# 중국어 → 한국어 번역
V4_TRANSLATIONS = {
    # 색상 21종
    "天缥青（奶油团长特调）": "스카이청록 (대표컬러)",
    "深棕": "진브라운",
    "闪黑": "펄블랙",
    "闪白": "펄화이트",
    "青芽绿（奶油团长特调）": "새싹그린",
    "青果绿": "풋그린",
    "浅紫": "연보라",
    "浅蓝": "연파랑",
    "浅咖": "연브라운",
    "浅黄": "연노랑",
    "浅粉": "연핑크",
    "奶玉": "크림제이드",
    "奶油粉（奶油团长特调）": "크림핑크",
    "奶蓝": "크림블루",
    "奶茶": "밀크티",
    "奶白（小恐龙特调）": "크림화이트",
    "抹茶绿": "말차그린",
    "曼波绿": "맘보그린",
    "红丝绒": "레드벨벳",
    "豆丁黄": "빈티지 옐로우",
    "超淡粉（紫调）（奶油团长特调）":
        "초연핑크",

    # 무게추 모듈
    "模组1：浅蓝、奶油粉、超淡粉":
        "모듈 1: 연파랑 · 크림핑크 · 초연핑크",
    "模组2：曼波绿、青芽绿、天缥青":
        "모듈 2: 맘보그린 · 새싹그린 · 스카이청록",
    "模组3：奶茶、奶白、奶玉":
        "모듈 3: 밀크티 · 크림화이트 · 크림제이드",
    "模组4：全奶白": "모듈 4: 전체 크림화이트",

    # 키보드 구성품
    "底壳": "하판",
    "上盖": "상판",
    "配重": "무게추",
    "屏幕框": "스크린 프레임",
    "铭牌": "명판",
    "固定底色": "고정 베이스 컬러",
    "正反面": "정면·후면",
    "侧面": "측면",

    # 사이트 UI
    "Dino75 V4 选色预览":
        "Dino75 V4 색상 조합 미리보기",
    "键盘预览": "키보드 미리보기",
    "选色控制": "색상 선택 영역",
    "固定预览": "미리보기 고정",
    "取消固定": "고정 해제",
    "注：本页面仅用于颜色搭配预览，具体颜色以实物和最终打样效果为准。":
        "※ 본 페이지는 색상 조합 미리보기용입니다. "
        "실제 색상은 제품 실물 및 최종 샘플을 기준으로 합니다.",
    "界面主题": "화면 테마",
    "浅色": "라이트",
    "暗色": "다크",
    "已选摘要": "선택한 옵션 요약",
    "正在读取默认搭配": "기본 색상 조합을 불러오는 중",
    "恢复默认": "기본값으로 초기화",
    "恢复": "초기화",
    "保存图片": "이미지 저장",
    "关闭预览": "미리보기 닫기",
    "关闭": "닫기",
    "公告": "공지",
    "主要部件": "주요 구성품",
    "必选": "필수",
    "外观颜色搭配": "외관 색상 조합",
    "随机搭配": "랜덤 조합",
    "当前配置": "현재 선택 옵션",
    "选择配置": "구성 선택",
    "选色预览": "색상 조합 미리보기",
    "Color Studio": "컬러 스튜디오",

    # 오류 및 상태 메시지
    "请检查素材路径": "이미지 파일 경로를 확인해 주세요",
    "当前选择没有可显示内容":
        "선택한 구성의 이미지를 표시할 수 없습니다",
    "缺少 ": "이미지 ",
    " 张素材，请检查文件名":
        "개가 누락되었습니다. 파일명을 확인해 주세요",
    "正在生成图片…": "이미지를 생성하는 중…",
    "生成预览图失败": "미리보기 이미지 생성 실패",
    "生成失败，请重试":
        "이미지 생성에 실패했습니다. 다시 시도해 주세요",
    "保存中...": "저장 중...",
    "Canvas 导出为空":
        "캔버스 이미지 내보내기 결과가 비어 있습니다",
    "选色预览-正反面-": "색상조합-정면후면-"
}


def safe_path(url):
    u = urlsplit(url)

    if u.hostname != HOST:
        return None

    path = unquote(u.path).lstrip("/")
    p = PurePosixPath(path or "index.html")

    if any(x in (".", "..") for x in p.parts):
        return None

    if "\\" in path or path.startswith("/"):
        return None

    if not p.suffix and u.path.endswith("/"):
        p /= "index.html"

    return Path(*p.parts)


def fix_html(raw, base):
    soup = BeautifulSoup(raw, "html.parser")

    for tag in soup.find_all(True):
        for attr in ("src", "href", "poster", "action", "data-src"):
            value = tag.attrs.get(attr)

            if (
                isinstance(value, str)
                and value.startswith("/")
                and not value.startswith("//")
            ):
                tag.attrs[attr] = base + value.lstrip("/")

        if (
            tag.name == "meta"
            and tag.get("http-equiv", "").lower()
            == "content-security-policy"
        ):
            tag.decompose()

    if soup.html:
        soup.html["lang"] = "ko"

    head = soup.head

    if not head:
        head = soup.new_tag("head")
        soup.html.insert(0, head)

    glossary_script = soup.new_tag(
        "script",
        src=base + "ko-dictionary.js"
    )

    localization_script = soup.new_tag(
        "script",
        src=base + "ko-localization.js",
        defer=""
    )

    head.append(glossary_script)
    head.append(localization_script)

    return str(soup)


def translate_source(source, glossary, is_js=False):
    """JS 내부 유니코드 중국어 및 HTML 문구를 번역합니다."""

    if is_js:
        def decode_unicode(match):
            code = int(match.group(1), 16)

            if code >= 0x2000:
                return chr(code)

            return match.group(0)

        source = re.sub(
            r"\\u([0-9a-fA-F]{4})",
            decode_unicode,
            source
        )

    # 긴 문자열부터 치환하여 부분 번역 충돌을 방지
    translations = sorted(
        glossary.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )

    for chinese, korean in translations:
        if chinese and chinese in source:
            source = source.replace(chinese, korean)

    return source


def run(repository, output):
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)

    repo = repository.split("/")[-1]

    if repo.endswith(".github.io"):
        base = "/"
    else:
        base = "/" + repo + "/"

    snapshot = {}
    warnings = []

    def store(url, body):
        rel = safe_path(url)

        if rel is None:
            return

        if len(body) > MAX_BYTES:
            return

        if len(snapshot) >= MAX_RESOURCES:
            return

        if urlsplit(url).path in ("", "/"):
            rel = Path("index.html")

        snapshot[str(rel)] = body

    # 원본 사이트 실행 및 리소스 수집
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 1440, "height": 1000},
            locale="zh-CN"
        )

        def received(res):
            if res.status != 200:
                return

            if urlsplit(res.url).hostname != HOST:
                return

            try:
                store(res.url, res.body())
            except Exception as exc:
                warnings.append(f"{res.url}: {exc}")

        page.on("response", received)

        page.goto(
            ORIGIN,
            wait_until="domcontentloaded",
            timeout=55000
        )

        page.wait_for_timeout(4000)

        html = page.request.get(
            ORIGIN,
            timeout=30000
        ).text()

        browser.close()

    session = requests.Session()

    session.headers.update({
        "User-Agent":
            "Mozilla/5.0 (Dino75 Korean Github Pages build)"
    })

    snapshot["index.html"] = html.encode("utf-8")

    # HTML/JS/CSS에 참조된 추가 리소스 수집
    allowed = re.compile(
        r"""(?<![A-Za-z0-9])/(?:(?:assets|static|images|image|img|data|fonts|icons|products|color|colors)/)[^\s"'`<>\\)]{1,250}""",
        re.I
    )

    for _ in range(3):
        references = set()

        for name, data in list(snapshot.items()):
            if Path(name).suffix.lower() not in (
                ".html", ".css", ".js", ".mjs", ".json"
            ):
                continue

            try:
                source = data.decode("utf-8")
            except UnicodeDecodeError:
                continue

            for match in allowed.findall(source):
                references.add(
                    match.split("?")[0].split("#")[0]
                )

            if name.endswith((".js", ".mjs", ".css")):
                matches = re.findall(
                    r"""["'](\.\.?/[^"']+\.(?:js|mjs|css|json|png|jpg|jpeg|webp|svg))["']""",
                    source,
                    re.I
                )

                for match in matches:
                    ref = "/" + str(
                        (PurePosixPath(name).parent / match)
                        .as_posix()
                    ).lstrip("/")

                    references.add(ref)

        count = 0

        for ref in sorted(references):
            loc = safe_path(ORIGIN.rstrip("/") + ref)

            if not loc:
                continue

            if str(loc) in snapshot:
                continue

            if len(snapshot) >= MAX_RESOURCES:
                continue

            try:
                res = session.get(
                    urljoin(ORIGIN, ref),
                    timeout=20
                )

                if res.ok and len(res.content) <= MAX_BYTES:
                    store(res.url, res.content)
                    count += 1

            except requests.RequestException as exc:
                warnings.append(f"{ref}: {exc}")

        if count == 0:
            break

    # 원본 JavaScript에서 색상 옵션 목록 추출
    app_source = snapshot.get(
        "app.js", b""
    ).decode("utf-8-sig", errors="replace")

    if not app_source:
        raise RuntimeError(
            "원본 app.js를 가져오지 못했습니다."
        )

    def option_ids(label):
        match = re.search(
            r"const\s+" + label + r"\s*=\s*\[(.*?)\];",
            app_source,
            re.S
        )

        if not match:
            raise RuntimeError(
                f"원본 app.js에서 {label}을 찾을 수 없습니다."
            )

        return list(dict.fromkeys(
            re.findall(
                r"""["']id["']\s*:\s*["'](opt\d+)["']""",
                match.group(1)
            )
        ))

    colors = option_ids("COLOR_OPTIONS")
    weights = option_ids("WEIGHT_OPTIONS")

    if not colors or not weights:
        raise RuntimeError(
            "원본 이미지 색상 옵션을 읽을 수 없습니다."
        )

    # 색상별 키보드 이미지 전체 수집
    # 첫 화면에서 요청되는 6장만 저장하는 문제 해결
    missing_paths = [
        f"webp/front/{folder}/{code}.webp"
        for folder in (
            "top",
            "bottom",
            "screen",
            "badge"
        )
        for code in colors
    ]

    missing_paths += [
        f"webp/front/weight/{code}.webp"
        for code in weights
    ]

    missing_paths += [
        "webp/front/base/opt001.webp"
    ]

    missing_paths = [
        key
        for key in dict.fromkeys(missing_paths)
        if key not in snapshot
    ]

    def fetch_image(key):
        try:
            res = requests.get(
                urljoin(ORIGIN, key),
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": ORIGIN
                },
                timeout=25
            )

            valid_type = (
                res.headers.get(
                    "content-type", ""
                ).startswith("image/")
                or res.content[:4] == b"RIFF"
            )

            if (
                res.ok
                and len(res.content) <= MAX_BYTES
                and valid_type
            ):
                return key, res.content

            return key, None

        except requests.RequestException:
            return key, None

    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [
            pool.submit(fetch_image, key)
            for key in missing_paths
        ]

        for future in as_completed(futures):
            key, data = future.result()

            if data:
                snapshot[key] = data
            else:
                warnings.append(
                    "이미지 수집 실패: " + key
                )

    images_stored = sum(
        key.startswith("webp/front/")
        and key.endswith(".webp")
        for key in snapshot
    )

    expected_images = (
        len(colors) * 4
        + len(weights)
        + 1
    )

    print(
        f"키보드 이미지 수집: "
        f"{images_stored}개 / "
        f"예상 {expected_images}개"
    )

    if images_stored < int(expected_images * 0.90):
        raise RuntimeError(
            f"키보드 이미지가 너무 적습니다 "
            f"({images_stored}개). 누락: "
            + ", ".join(warnings[-12:])
        )

    # 기존 번역표 + Dino75 V4 전용 번역표
    glossary = json.loads(
        Path(
            "assets/overrides.json"
        ).read_text(encoding="utf-8")
    )

    glossary.update(V4_TRANSLATIONS)

    # 배포용 사이트 파일 생성
    for path, body in snapshot.items():
        rel = Path(path)
        dest = target / rel

        dest.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if path == "index.html":
            html_output = fix_html(
                html,
                base
            )

            dest.write_text(
                translate_source(
                    html_output,
                    glossary
                ),
                encoding="utf-8"
            )

        elif rel.suffix.lower() in (".js", ".mjs"):
            # 이미지 경로에 GitHub 저장소명이
            # 중복 삽입되지 않도록 원본 JS 경로 유지
            js_source = body.decode(
                "utf-8-sig",
                errors="replace"
            )

            if path in (
                "app.js",
                "announcement.js"
            ):
                js_source = translate_source(
                    js_source,
                    glossary,
                    is_js=True
                )

            dest.write_text(
                js_source,
                encoding="utf-8"
            )

        else:
            dest.write_bytes(body)

    # 중국어 미번역 문구 확인
    for relpath in (
        "index.html",
        "app.js",
        "announcement.js"
    ):
        file = target / relpath

        if not file.exists():
            continue

        unresolved = sorted(set(
            re.findall(
                r"[\u3400-\u9fff]+",
                file.read_text(encoding="utf-8")
            )
        ))

        if unresolved:
            raise RuntimeError(
                "한국어 누락 (" + relpath + "): "
                + ", ".join(unresolved[:30])
            )

    # 클라이언트 번역 사전 생성
    (target / "ko-dictionary.js").write_text(
        "window.DINO75_KO = "
        + json.dumps(
            glossary,
            ensure_ascii=False
        )
        + ";\n",
        encoding="utf-8"
    )

    # 동적 화면 번역 스크립트
    (target / "ko-localization.js").write_bytes(
        Path(
            "assets/localization.js"
        ).read_bytes()
    )

    # GitHub Pages 정적 배포 설정
    (target / ".nojekyll").touch()

    # 404 페이지
    (target / "404.html").write_text(
        '<!doctype html>'
        '<html lang="ko">'
        '<meta charset="utf-8">'
        '<title>페이지를 찾을 수 없습니다</title>'
        f'<a href="{base}">'
        'Dino75 V4 한국어로 돌아가기'
        '</a></html>',
        encoding="utf-8"
    )

    # 빌드 결과 보고서
    (target / "build-report.json").write_text(
        json.dumps(
            {
                "source": ORIGIN,
                "base": base,
                "resource_count": len(snapshot),
                "warnings": warnings[:100]
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"정적 페이지 생성 완료: "
        f"{len(snapshot)} resources; "
        f"Pages base={base}"
    )

    if not any(
        key.endswith(".js")
        for key in snapshot
    ):
        print(
            "경고: JS 리소스가 수집되지 않았습니다."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repository",
        required=True,
        help="username/repo"
    )

    parser.add_argument(
        "--output",
        default="site"
    )

    args = parser.parse_args()

    run(
        args.repository,
        args.output
    )
