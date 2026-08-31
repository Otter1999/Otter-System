import json, os, sys, time, urllib.request, urllib.parse, urllib.error

STOCKS = [
    ("한국전력", "015760"), ("한전기술", "052690"), ("HD현대일렉트릭", "267260"),
    ("유진테크", "084370"), ("한미반도체", "042700"), ("하나마이크론", "067310"), ("테스", "095610"), ("티엘비", "356860"),
    ("HD현대중공업", "329180"), ("삼성중공업", "010140"),
    ("LG전자", "066570"), ("LG이노텍", "011070"), ("삼성전기", "009150"), ("삼성SDI", "006400"),
    ("GS건설", "006360"), ("삼성물산", "028260"), ("두산", "000150"), ("두산에너빌리티", "034020"),
    ("OCI홀딩스", "010060"), ("태광", "023160"), ("성광벤드", "014620"), ("대한항공", "003490"), ("파마리서치", "214450"),
]

BASE = "https://openapi.koreainvestment.com:9443"


def http(method, url, headers=None, body=None, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": True, "status": e.code, "body": e.read().decode(errors="replace")}


def get_token(appkey, appsecret):
    resp = http("POST", BASE + "/oauth2/tokenP",
                headers={"content-type": "application/json"},
                body={"grant_type": "client_credentials", "appkey": appkey, "appsecret": appsecret})
    if "access_token" not in resp:
        raise RuntimeError(f"토큰 발급 실패: {resp}")
    return resp["access_token"]


def investor_flow(appkey, appsecret, token, code):
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": appkey, "appsecret": appsecret,
        "tr_id": "FHKST01010900", "custtype": "P",
    }
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
    return http("GET", BASE + "/uapi/domestic-stock/v1/quotations/inquire-investor",
                headers=headers, params=params)


def main():
    appkey = os.environ["KIS_APPKEY"]
    appsecret = os.environ["KIS_APPSECRET"]
    token = get_token(appkey, appsecret)
    results = {}
    for name, code in STOCKS:
        for attempt in range(3):
            r = investor_flow(appkey, appsecret, token, code)
            if not (isinstance(r, dict) and r.get("error")):
                break
            time.sleep(1.5)
        results[code] = {"name": name, "data": r}
        time.sleep(0.5)
    os.makedirs("data", exist_ok=True)
    with open("data/investor_flow.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
