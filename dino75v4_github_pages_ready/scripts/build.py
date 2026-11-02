#!/usr/bin/env python3
"""GitHub Pages용 원본 사이트 정적 스냅샷 생성.

실제 소스 HTML/JS/이미지는 CI에서 원본 서버에 접근해 가져온다.
이 정적 복제는 원본 페이지가 서버 POST/API에 의존할 때 완전 호환되지 않을 수 있다.
"""
import argparse
import json
import mimetypes
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urljoin, urlsplit, unquote
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ORIGIN = 'https://dino75v4.xiaojiu99.top/'
HOST = urlsplit(ORIGIN).hostname
MAX_BYTES = 25 * 1024 * 1024
MAX_RESOURCES = 900


def safe_path(url: str):
    u = urlsplit(url)
    if u.hostname != HOST:
        return None
    path = unquote(u.path).lstrip('/')
    p = PurePosixPath(path or 'index.html')
    if any(x in ('.', '..') for x in p.parts) or '\\' in path or path.startswith('/'):
        return None
    if not p.suffix and u.path.endswith('/'):
        p /= 'index.html'
    return Path(*p.parts)


def rewrite_root_paths(text: str, base: str):
    """수집한 원본 리소스의 root-relative URLs를 Pages 하위 경로로 변경."""
    # root url in HTML attributes and JS/CSS string literals
    text = re.sub(r'(?P<prefix>["\'\(=])/(?!/|'+re.escape(base.lstrip('/'))+r')',
                  lambda m: m.group('prefix') + base, text)
    text = re.sub(r'url\(\s*/(?!/|'+re.escape(base.lstrip('/'))+r')',
                  lambda m: m.group(0)[:-1] + base, text, flags=re.I)
    return text


def fix_html(raw: str, base: str):
    soup = BeautifulSoup(raw, 'html.parser')
    for tag in soup.find_all(True):
        for attr in ('src','href','poster','action','data-src'):
            v = tag.attrs.get(attr)
            if isinstance(v,str) and v.startswith('/') and not v.startswith('//'):
                tag.attrs[attr] = base + v.lstrip('/')
        if tag.name == 'meta' and tag.get('http-equiv','').lower() == 'content-security-policy':
            tag.decompose()
    if soup.html: soup.html['lang'] = 'ko'
    head = soup.head
    if not head:
        head=soup.new_tag('head')
        soup.html.insert(0,head)
    # Paths are project-root-relative; loads glossary before translation script.
    js_gloss=soup.new_tag('script',src=base+'ko-dictionary.js')
    js_local=soup.new_tag('script',src=base+'ko-localization.js',defer='')
    head.append(js_gloss)
    head.append(js_local)
    return str(soup)


def run(repository: str, output: str):
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    repo = repository.split('/')[-1]
    base = '/' if repo.endswith('.github.io') else '/'+repo+'/'
    snapshot = {}
    warnings = []

    def store(url, body):
        rel = safe_path(url)
        if rel is None or len(body) > MAX_BYTES or len(snapshot) >= MAX_RESOURCES:
            return
        if urlsplit(url).path in ('','/'):
            rel = Path('index.html')
        # Only 2xx response bodies should reach here.
        snapshot[str(rel)] = body

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000},locale='zh-CN')
        def received(res):
            if res.status != 200 or urlsplit(res.url).hostname!=HOST:
                return
            try:
                body=res.body()
                store(res.url,body)
            except Exception as exc:
                warnings.append(f'{res.url}: {exc}')
        page.on('response',received)
        page.goto(ORIGIN,wait_until='domcontentloaded',timeout=55000)
        page.wait_for_timeout(4000)
        # 캡처하는 요청들은 이전에 선택하지 않았던 옵션에서도 발생할 수 있다.
        # 일괄 클릭은 원본 선택 상태를 변경하므로 여기서는 실행하지 않는다.
        html=page.request.get(ORIGIN,timeout=30000).text()
        browser.close()

    session=requests.Session()
    session.headers.update({'User-Agent':'Mozilla/5.0 (Dino75 Korean Github Pages build)'})

    # 원본 HTML을 우선 사용해 원본 SPA 초기화 코드를 보존한다.
    snapshot['index.html'] = html.encode('utf-8')
    # 리소스 문자열에 언급된 이미지/JS/JSON 등을 추가로 수집한다.
    allowed=re.compile(r'(?<![A-Za-z0-9])/(?:(?:assets|static|images|image|img|data|fonts|icons|products|color|colors)/)[^\s"\'`<>\\)]{1,250}',re.I)
    for _ in range(3):
        references=set()
        for name,data in list(snapshot.items()):
            if Path(name).suffix.lower() not in ('.html','.css','.js','.mjs','.json'):
                continue
            try: source=data.decode('utf-8')
            except UnicodeDecodeError: continue
            for match in allowed.findall(source):
                references.add(match.split('?')[0].split('#')[0])
            if name.endswith(('.js','.mjs','.css')):
                for match in re.findall(r'["\'](\.\.?/[^"\']+\.(?:js|mjs|css|json|png|jpg|jpeg|webp|svg))["\']',source,re.I):
                    references.add('/'+str((PurePosixPath(name).parent/match).as_posix()).lstrip('/'))
        count=0
        for ref in sorted(references):
            loc=safe_path(ORIGIN.rstrip('/')+ref)
            if not loc or str(loc) in snapshot or len(snapshot)>=MAX_RESOURCES:
                continue
            try:
                res=session.get(urljoin(ORIGIN,ref),timeout=20)
                if res.ok and len(res.content)<=MAX_BYTES:
                    store(res.url,res.content)
                    count+=1
            except requests.RequestException as exc:
                warnings.append(f'{ref}: {exc}')
        if count==0: break

    for path,body in snapshot.items():
        rel=Path(path)
        dest=target/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        if path == 'index.html':
            dest.write_text(fix_html(html,base),encoding='utf-8')
        elif rel.suffix.lower() in ('.css','.js','.mjs'):
            try:
                dest.write_text(rewrite_root_paths(body.decode('utf-8'),base),encoding='utf-8')
            except UnicodeDecodeError:
                dest.write_bytes(body)
        else:
            dest.write_bytes(body)

    glossary=json.loads(Path('assets/overrides.json').read_text(encoding='utf-8'))
    (target/'ko-dictionary.js').write_text('window.DINO75_KO = '+json.dumps(glossary,ensure_ascii=False)+';\n',encoding='utf-8')
    (target/'ko-localization.js').write_bytes(Path('assets/localization.js').read_bytes())
    (target/'.nojekyll').touch()
    (target/'404.html').write_text('''<!doctype html><html lang="ko"><meta charset="utf-8"><title>페이지를 찾을 수 없습니다</title><a href="'''+base+'''">Dino75 V4 한국어로 돌아가기</a></html>''',encoding='utf-8')
    (target/'build-report.json').write_text(json.dumps({
        'source':ORIGIN,'base':base,'resource_count':len(snapshot),
        'warnings':warnings[:100]
    },ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'정적 페이지 생성 완료: {len(snapshot)} resources; Pages base={base}')
    if not any(k.endswith('.js') for k in snapshot):
        print('경고: JS 리소스가 수집되지 않았습니다. 원본이 정상 동작하는지 점검하세요.')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--repository',required=True,help='username/repo')
    ap.add_argument('--output',default='site')
    args=ap.parse_args()
    run(args.repository,args.output)
