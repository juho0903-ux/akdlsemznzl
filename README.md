# 오늘의 마음쿠키 — 학생용 앱 + 담임 구글 시트 기록

## 1. GitHub에 올리기
기존 저장소에 아래 **5개 파일**을 같은 이름으로 업로드하고 `Commit changes`를 누릅니다.

- `app.py` (기존 파일 교체)
- `emotions.json` (기존 파일 교체, 121개 감정 유지)
- `requirements.txt` (기존 파일 교체)
- `fortune_cookie.png` (추가: 쿠키가 열릴 때 사용되는 그림)
- `README.md` (선택: 사용 설명서)

`fortune_cookie.png`도 반드시 업로드해야 합니다. Streamlit 앱 시작 파일은 `app.py`입니다.

## 2. 구글 스프레드시트 생성
1. 선생님 구글 계정으로 Google Sheets에서 빈 스프레드시트를 만들고, 이름을 `오늘의 마음쿠키 기록`처럼 정합니다.
2. 스프레드시트 주소는 `https://docs.google.com/spreadsheets/d/스프레드시트ID/edit` 꼴입니다. `/d/`와 `/edit` 사이 **스프레드시트ID**를 복사해 둡니다.
3. 구글 클라우드 콘솔(https://console.cloud.google.com/)에서 프로젝트를 생성하고 **Google Sheets API**와 **Google Drive API**를 활성화합니다.
4. Google Cloud Console → IAM 및 관리자 → 서비스 계정 → 서비스 계정 만들기. 해당 서비스 계정에서 **키 → 키 추가 → 새 키 만들기 → JSON**을 발급받습니다.
5. JSON 안의 `client_email` 주소에 스프레드시트를 **편집자** 권한으로 공유합니다. **전체 공개로 공유하면 안 됩니다.**
6. JSON에 들어있는 값들을 Streamlit Community Cloud → 앱 `Settings` → `Secrets`에 아래 형식으로 입력합니다. 이 값들을 GitHub 파일로 업로드하지 마세요.

```toml
spreadsheet_id = "여기에_구글_시트_ID"

[gcp_service_account]
type = "service_account"
project_id = "JSON의_project_id"
private_key_id = "JSON의_private_key_id"
private_key = "JSON의_private_key_전체_내용_줄바꿈은_\\n으로_표시"
client_email = "JSON의_client_email"
client_id = "JSON의_client_id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "JSON의_client_x509_cert_url"
universe_domain = "googleapis.com"
```

`private_key`는 **JSON에 있는 실제 값을 그대로** 옮깁니다. TOML에 한 줄 문자열로 붙일 때 `\n` 표기를 유지합니다. JSON에 위에서 생략된 속성이 있다면 함께 넣어도 됩니다.

7. Secrets 저장 후 Streamlit 앱을 다시 열어 테스트 학생 명단 하나를 선택하고 감정 하나를 눌러 쿠키를 엽니다. 최초 제출 시 시트에 **`마음기록`** 탭이 자동 생성됩니다.
8. 구글 시트에서 시각·번호·이름·감정1·감정2·담임 메시지·쿠키 메시지를 확인하세요.

## 3. 제출과 개인정보
- **번호 및 이름 선택**: 1~28번을 드롭다운에서 클릭합니다. 번호는 입력 순서대로 지정되어 있습니다.
- **감정**: 1~2개 선택. **담임에게 보내는 말**: 선택 사항.
- `마음쿠키 열기 · 오늘의 마음 제출`을 누르면 Google Sheets에 **한 줄** 저장한 후 메시지를 보여 줍니다.
- 저장에 실패하면 완료 메시지를 표시하지 않습니다. 같은 감정으로 다른 쿠키 문구를 볼 때는 **추가 저장되지 않습니다.**
- 아이가 번호와 이름을 고르는 방식은 **본인 인증이 아니므로** 서로의 이름으로 제출할 수 있습니다. 실제 본인 인증은 계정 로그인 등 별도 체계가 필요합니다.
- 이 정보는 학생을 식별할 수 있는 개인 기록입니다. GitHub에 **명단 파일 외에** 제출 기록, 서비스 계정 키, 실제 스프레드시트 내용을 올리지 마세요. **가능하면 GitHub 저장소를 비공개**로 두고, 교내 개인정보 처리 지침과 학부모·학생 안내에 맞춰 운용하세요.
- 교사가 당장 메시지를 확인하거나 응답한다는 보장은 없습니다. 즉시 도움이 필요한 학생은 직접 교사에게 연락하도록 앱에 안내했습니다.
- Google Sheets: `파일 → 다운로드 → Microsoft Excel(.xlsx)`로 엑셀 파일을 받을 수 있습니다.

## 4. 이후 수정 방식
- 화면·애니메이션·기록 기능 변경: 같은 이름의 `app.py`를 교체.
- 문구 변경: 같은 이름의 `emotions.json`을 교체.
- 라이브러리 변경: `requirements.txt`를 교체.
- 쿠키 그림 변경: `fortune_cookie.png`를 교체.

**중요:** 서비스 계정 키나 스프레드시트 ID는 채팅에 공개하지 말고 Streamlit Secrets에만 입력하세요.
