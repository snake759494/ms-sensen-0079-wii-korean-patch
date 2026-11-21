# 재빌드

## 준비물

- Python 3.11 이상
- `Pillow` (`pip install pillow`)
- Git for Windows의 bash (`build.py`가 `cp -al`로 작업 폴더를 만듭니다)
- Dolphin에 들어 있는 `DolphinTool.exe`
- [Wiimms ISO Tools](https://wit.wiimm.de/)의 `wit.exe`
- 원본 일본판 R79JAF 디스크(RVZ 또는 ISO)
  - ISO로 바꿨을 때 MD5가 README 표의 값이어야 합니다.
- 글꼴(`docs/FONT_CREDITS.md`). 저장소 최상위의 `fonts/` 폴더에 둡니다.
- (배포 파일을 만들 때) xdelta3

## 순서

저장소 최상위에서 실행합니다.

```powershell
.\DolphinTool.exe convert -i '.\Kidou Senshi Gundam - MS Sensen 0079 (Japan).rvz' -o orig.iso -f iso
.\DolphinTool.exe extract -i orig.iso -o ext
```

`ext/DATA/files/`와 `ext/DATA/sys/main.dol`이 있어야 합니다. 그다음 원문 목록을 디스크에서 뽑습니다(일본어 원문은 저장소에 넣지 않았으므로 직접 만듭니다).

```powershell
python tools/extract.py   # text/all.json  (화면·lua 문자열, 번호는 text/tr/*.json과 대응)
python tools/gevext.py    # text/gev.json  (튜토리얼 문장, 번호는 text/tr_gev.json과 대응)
python tools/build.py     # patch/, patch_sys/main.dol 생성
wit.exe copy orig.iso dec.iso --enc decrypt --psel whole
python tools/inject.py dec.iso            # 바뀐 파일을 원본 배치 그대로 넣기
python tools/inject.py rehash dec.iso     # H0~H3 해시 다시 계산
wit.exe copy dec.iso 'Kidou Senshi Gundam - MS Sensen 0079 (Korean).iso' --enc encrypt --psel whole
python tools/inject.py restore dec.iso 'Kidou Senshi Gundam - MS Sensen 0079 (Korean).iso' orig.iso
python tools/inject.py fixtmd 'Kidou Senshi Gundam - MS Sensen 0079 (Korean).iso'
wit.exe verify 'Kidou Senshi Gundam - MS Sensen 0079 (Korean).iso'
```

`build.py`가 하는 일은 다음과 같습니다.
1. `.arc`·`.xbf`·`.lua`·`.gev`·`.brfnt` 파일을 찾아 U8 아카이브를 재귀적으로 풀고, XBF·lua 문자열과 튜토리얼 문장을 번역문으로 바꿉니다.
2. 게임 글꼴(`NORMAL_FONT`·`IN_GAME_FONT`)의 한자 슬롯에 한글을 그립니다.
3. brres 안의 그림 글자(미션 제목·전투 표시 등)를 한글로 다시 그립니다.
4. `main.dol`에 튜토리얼용 한글 글리프와 후킹 코드를 넣습니다.
5. `ext/DATA`를 하드 링크로 `wfs/`에 복사하고, 바뀐 파일만 덮어씁니다. (`wfs/`는 Dolphin에서 폴더째 실행해 볼 때 씁니다.)

전체 아카이브를 훑기 때문에 10분 이상 걸립니다.

`wit copy wfs ...`로 ISO를 새로 만들면 파일 배치가 원본과 달라져 데이터 파티션 전체가 바뀌고, xdelta가 2GB를 넘습니다(GitHub 첨부 한도 초과). 그래서 `inject.py`로 원본 이미지를 복호화한 상태에서 바뀐 파일만 넣습니다.
- 크기가 같거나 작아진 파일은 원래 자리에, 커진 파일과 커진 `main.dol`은 파티션의 빈 구간에 쓰고 FST·boot.bin의 위치를 고칩니다.
- `rehash`로 해시를 다시 계산하고 `wit`로 암호화한 뒤, 어떤 파일도 쓰지 않는 2MB 해시 그룹은 `restore`로 원본 암호화 데이터와 H3 값을 되돌립니다(원본의 빈 영역 데이터는 wit가 그대로 재현하지 못하기 때문입니다).
- `fixtmd`가 H3 표 해시를 TMD에 넣고 가짜 서명합니다. `wit verify`에서 `TMD is fake signed`, `+OK`가 나와야 합니다.

## 배포 파일 만들기

```powershell
xdelta3 -e -0 -S none -A -B 2147483648 -s orig.iso '.\Kidou Senshi Gundam - MS Sensen 0079 (Korean).iso' MS_Sensen_0079_Wii_KO_v1.0.xdelta
```

결과 ISO의 SHA-256이 README 표의 값과 같으면 배포판과 같은 결과입니다.
이 절차로 배포판과 바이트 단위로 같은 ISO가 나오는 것을 확인했습니다.
