# Dino75 V4 한국어 · GitHub Pages 배포용

원본: https://dino75v4.xiaojiu99.top/

## 사용 방법

1. GitHub에서 **New repository** → 이름 `dino75v4-ko` → **Public** → Create repository.
2. 이 ZIP을 **압축 해제**하고 그 안의 모든 파일/폴더(`.github`, `assets`, `scripts` 포함)를 저장소에 업로드 후 커밋합니다. ZIP 파일 하나만 업로드하면 안 됩니다.
3. 저장소 **Settings → Pages → Build and deployment → Source → GitHub Actions**로 설정합니다.
4. **Actions**에서 `한국어 Dino75 V4 사이트 게시`가 성공했는지 확인합니다. 필요하면 Actions → Workflow → **Run workflow**로 수동 실행합니다.
5. 사이트 주소: `https://GITHUB_ID.github.io/dino75v4-ko/` (GITHUB_ID는 자신의 GitHub 사용자명).

## 작동 방식 및 중요한 한계

- GitHub Actions 실행 중 원본 사이트 HTML/JavaScript/CSS/이미지를 수집하여 정적 스냅샷을 만들고, 한국어 번역 레이어를 삽입해 Pages에 배포합니다.
- 기본 번역 용어는 `assets/overrides.json`에서 변경할 수 있습니다.
- 이 방식은 원본 서버와 완전히 독립된 1:1 복제라고 보장할 수 없습니다. **선택할 때 추가로 내려받는 이미지**, 인증/API 요청, 서버가 동적으로 생성하는 데이터는 빠질 수 있습니다.
- 고유 이름이나 새로 추가된 중국어가 용어집에 없는 경우 **중국어가 남습니다**. 자동 번역 서버는 GitHub Pages에서 실행하지 않습니다.
- 원본 도메인이 이쪽 환경에서 네트워크 접근되지 않아 실제 색상 선택/이미지 저장 동작을 직접 검증하지 못했습니다. 첫 배포 후 확인해야 합니다.
- `site/build-report.json`은 Actions의 배포 산출물에 포함되며 수집된 파일 수를 확인할 수 있습니다.
- 원본 이미지를 그대로 재사용하거나 공개하려면 원 저작권자·운영자의 사용 허락 범위를 확인해야 합니다.

## 업데이트

`assets/overrides.json`에서 번역을 수정하고 `main`에 커밋하면 사이트가 다시 배포됩니다.

## 참고

GitHub Pages는 Python 서버를 실행할 수 없습니다. 이 프로젝트는 이전 `app.py` 기반 프록시 방식이 아닌 정적 사이트 + GitHub Actions 빌드 방식입니다.
