import os
import json
import time
import urllib.request
import urllib.error

APPKEY = os.environ["KIS_APPKEY"]
APPSECRET = os.environ["KIS_APPSECRET"]
BASE = "https://openapi.koreainvestment.com:9443"

STOCKS = [
    ("한국전력", "015760"), ("한전기술", "052690"), ("HD현대일렉트릭", "267260"),
    ("유진테크", "084370"), ("한미반도체", "042700"), ("하나마이크론", "067310"), ("테스", "095610"), ("티엘비", "356860"),
    ("HD현대중공업", "329180"), ("삼성중공업", "010140"),
    ("LG전자", "066570"), ("LG이노텍", "011070"), ("삼성전기", "009150"), ("삼성SDI", "006400"),
    ("GS건설", "006360"), ("삼성물산", "028260"), ("두산", "000150"), ("두산에너빌리티", "034020"),
    ("OCI홀딩스", "010060"), ("태광", "023160"), ("성광벤드", "014620"), ("대한항공", "003490"), ("파마리서치", "214450"),
]


def http(method, path, headers=None, body=None):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body_txt = e.read().decode("utf-8")
        except Exception:
            body_txt = ""
        return {"error": True, "status": e.code, "body": body_txt}
    except Exception as e:
        return {"error": True, "exception": str(e)}


def get_token():
    body = {"grant_type": "client_credentials", "appkey": APPKEY, "appsecret": APPSECRET}
    headers = {"content-type": "application/json; charset=utf-8"}
    res = http("POST", "/oauth2/tokenP", headers, body)
    if "access_token" not in res:
        raise RuntimeError(f"token issue failed: {res}")
    return res["access_token"]


def investor_flow(token, code):
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APPKEY,
        "appsecret": APPSECRET,
        "tr_id": "FHKST01010900",
        "custtype": "P",
    }
    path = f"/uapi/domestic-stock/v1/quotations/inquire-investor?FID_COND_MRKT_DIV_CODE=J&FID_INPUT_ISCD={code}"
    return http("GET", path, headers)


def main():
    token = get_token()
    results = {}

    for name, code in STOCKS:
        ok = False
        last = None
        for attempt in range(3):
            data = investor_flow(token, code)
            last = data
            if not data.get("error") and data.get("rt_cd") == "0" and data.get("output"):
                latest = data["output"][0]
                results[code] = {
                    "name": name,
                    "date": latest.get("stck_bsop_date"),
                    "frgn_ntby_tr_pbmn": latest.get("frgn_ntby_tr_pbmn"),
                    "orgn_ntby_tr_pbmn": latest.get("orgn_ntby_tr_pbmn"),
                    "prsn_ntby_tr_pbmn": latest.get("prsn_ntby_tr_pbmn"),
                }
                ok = True
                break
            time.sleep(2.0)
        if not ok:
            results[code] = {"name": name, "failed": True, "last_error": last}
            print(f"FAILED: {name}({code}) -> {last}")
        else:
            print(f"OK: {name}({code})")
        time.sleep(1.0)

    os.makedirs("data", exist_ok=True)
    payload = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
    }
    with open("data/investor_flow.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    failed = [f"{v['name']}({k})" for k, v in results.items() if v.get("failed")]
    print(f"Done. {len(results) - len(failed)}/{len(STOCKS)} succeeded.")
    if failed:
        print("Failed stocks:", ", ".join(failed))


if __name__ == "__main__":
    main()
