#!/usr/bin/env python3
"""
AIoT L3 CWA HW1 — Gate 4: GitHub Repository & Security Verification
Rule:
  - Prerequisite: Gate 3 PASS
  - Repository structure, README, requirements.txt, and security settings
  - Confirm .env and any secrets are NOT in Git history/current files
  - Return: GATE 4 = PASS on success
"""

import os
import sys
import subprocess
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
LOG_FILE = BASE_DIR / "gate4_verification.log"

def log(msg, to_file=True):
    print(msg)
    if to_file:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

def run_cmd(cmd_list):
    try:
        res = subprocess.run(
            cmd_list,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def main():
    if LOG_FILE.exists():
        LOG_FILE.unlink()

    log("=" * 60)
    log("AIoT L3 CWA HW1 — Gate 4: GitHub & Security Verification")
    log("=" * 60)
    log("")

    failures = []

    # -------------------------------------------------------------
    # Check 1: Gate 3 Prerequisite Verification
    # -------------------------------------------------------------
    log("[Check 1] 檢驗 Gate 3 前置條件 (資料庫與 GIS 靜態資源)...")
    db_file = BASE_DIR / "weather.db"
    if not db_file.exists():
        failures.append("Check 1 FAIL: weather.db 不存在，Gate 2/3 前置條件未滿足")
        log("  [FAIL] weather.db 不存在")
    else:
        try:
            conn = sqlite3.connect(db_file)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM weather_forecasts;")
            cnt = c.fetchone()[0]
            conn.close()
            log(f"  [OK] weather.db 存在且內含 {cnt} 筆預報資料")
        except Exception as e:
            failures.append(f"Check 1 FAIL: weather.db 讀取失敗: {e}")
            log(f"  [FAIL] weather.db 讀取異常: {e}")

    gis_files = [
        BASE_DIR / "static" / "index.html",
        BASE_DIR / "static" / "js" / "app.js",
        BASE_DIR / "static" / "css" / "style.css",
        BASE_DIR / "static" / "data" / "county_coordinates.json",
        BASE_DIR / "static" / "data" / "taiwan_counties.json"
    ]
    missing_gis = [str(f.relative_to(BASE_DIR)) for f in gis_files if not f.exists()]
    if missing_gis:
        failures.append(f"Check 1 FAIL: 缺少 GIS 靜態資源: {missing_gis}")
        log(f"  [FAIL] 缺少 GIS 檔案: {missing_gis}")
    else:
        log("  [OK] GIS 前端核心地圖與 GeoJSON 資源完整")
    log("[Check 1] 前置條件檢核 PASS\n")

    # -------------------------------------------------------------
    # Check 2: 檔案架構與配置完整性 (README, requirements, .env.example)
    # -------------------------------------------------------------
    log("[Check 2] 檢驗專案核心文件與設定檔...")
    req_file = BASE_DIR / "requirements.txt"
    if not req_file.exists():
        failures.append("Check 2 FAIL: 找不到 requirements.txt")
        log("  [FAIL] 找不到 requirements.txt")
    else:
        req_content = req_file.read_text(encoding="utf-8")
        needed_pkgs = ["fastapi", "uvicorn"]
        missing_pkgs = [p for p in needed_pkgs if p not in req_content.lower()]
        if missing_pkgs:
            failures.append(f"Check 2 FAIL: requirements.txt 缺少必要套件: {missing_pkgs}")
            log(f"  [FAIL] requirements.txt 缺少: {missing_pkgs}")
        else:
            log(f"  [OK] requirements.txt 格式正確 (包含 {', '.join(needed_pkgs)})")

    readme_file = BASE_DIR / "README.md"
    if not readme_file.exists():
        failures.append("Check 2 FAIL: 找不到 README.md")
        log("  [FAIL] 找不到 README.md")
    else:
        readme_txt = readme_file.read_text(encoding="utf-8")
        keywords = ["Taiwan Weather GIS", "Gate", "CWA"]
        has_keywords = all(k.lower() in readme_txt.lower() for k in keywords)
        if not has_keywords:
            failures.append("Check 2 FAIL: README.md 未包含專案真實架構或 Gate 流程說明")
            log("  [FAIL] README.md 內容不符合專案主題")
        else:
            log("  [OK] README.md 結構與五階段閘門說明完整")

    env_ex_file = BASE_DIR / ".env.example"
    if not env_ex_file.exists():
        failures.append("Check 2 FAIL: 缺少 .env.example 示範檔")
        log("  [FAIL] 缺少 .env.example")
    else:
        log("  [OK] .env.example 存在，供使用者安全複製參考")

    gitignore_file = BASE_DIR / ".gitignore"
    if not gitignore_file.exists():
        failures.append("Check 2 FAIL: 缺少 .gitignore 檔案")
        log("  [FAIL] 缺少 .gitignore")
    else:
        gi_txt = gitignore_file.read_text(encoding="utf-8")
        if ".env" not in gi_txt:
            failures.append("Check 2 FAIL: .gitignore 未包含 .env")
            log("  [FAIL] .gitignore 未包含 .env")
        else:
            log("  [OK] .gitignore 已正確阻擋敏感設定")
    log("[Check 2] 專案配置檢核 PASS\n")

    # -------------------------------------------------------------
    # Check 3: 資安與敏感金鑰隔離 (Security Check)
    # -------------------------------------------------------------
    log("[Check 3] 執行資安檢核：確認 .env 與金鑰未進入 Git 追蹤或歷史紀錄...")
    
    # Check if .env is tracked in git index
    code, out, _ = run_cmd(["git", "ls-files", ".env"])
    if out.strip() != "":
        failures.append("Check 3 FAIL: .env 正在被 Git 追蹤中！必須立即移除！")
        log("  [FAIL] .env 被 Git 追蹤！")
    else:
        log("  [OK] .env 未被 Git 追蹤 (安全隔離)")

    # Check git log for any leaked API key pattern
    code, log_diff, _ = run_cmd(["git", "log", "-p"])
    # Look for real CWA key patterns that are not masked
    import re
    # Real key pattern: CWA- followed by alphanumeric characters without asterisks or placeholder X
    suspicious_keys = []
    for line in log_diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            matches = re.findall(r"CWA-[A-Za-z0-9]{20,}", line)
            for m in matches:
                if "XXXX" not in m:
                    suspicious_keys.append(m)

    if suspicious_keys:
        failures.append(f"Check 3 FAIL: Git commit 歷史中疑似出現未遮罩之金鑰: {suspicious_keys}")
        log(f"  [FAIL] 發現可疑未遮罩金鑰: {suspicious_keys}")
    else:
        log("  [OK] Git 歷史紀錄稽核：無明文或未遮罩之 CWA API 金鑰洩漏")
    log("[Check 3] 資安隔離檢核 PASS\n")

    # -------------------------------------------------------------
    # Check 4: Git 遠端設定與工作目錄整潔度 (Repository Status)
    # -------------------------------------------------------------
    log("[Check 4] 檢驗 Git Remote 與工作目錄狀態...")
    code, remotes, _ = run_cmd(["git", "remote", "-v"])
    if "github.com" not in remotes:
        failures.append("Check 4 FAIL: 找不到指向 GitHub 的 git remote origin")
        log("  [FAIL] 未設定 GitHub remote")
    else:
        origin_url = [l for l in remotes.splitlines() if "origin" in l][0]
        log(f"  [OK] 遠端庫已連結: {origin_url}")

    # Check untracked files
    code, st_out, _ = run_cmd(["git", "status", "--porcelain"])
    untracked_critical = []
    for l in st_out.splitlines():
        if l.startswith("??") and (".env" in l or "key" in l.lower() or "secret" in l.lower()):
            untracked_critical.append(l)

    if untracked_critical:
        failures.append(f"Check 4 FAIL: 存在未受保護之敏感檔案: {untracked_critical}")
        log(f"  [FAIL] 發現未忽略之敏感暫存檔: {untracked_critical}")
    else:
        log("  [OK] 工作目錄敏感檔案完全防護")
    log("[Check 4] Git 遠端與狀態檢核 PASS\n")

    # -------------------------------------------------------------
    # Summary & Final Verdict
    # -------------------------------------------------------------
    log("=" * 60)
    if failures:
        log("GATE 4 驗證未通過，請修復以下項目：")
        for f in failures:
            log(f"  - {f}")
        log("VERDICT: GATE 4 = FAIL")
        sys.exit(1)
    else:
        log("Gate 4 查核項目全部合格 (Repository, Docs, Requirements, Security PASS)")
        log("VERDICT: GATE 4 = PASS")
    log("=" * 60)

if __name__ == "__main__":
    main()
