# -*- coding: utf-8 -*-
"""把 gh-pages 目录发布到 GitHub Pages。用法: python _deploy.py <github_token>"""
import sys, os, json, time, subprocess, urllib.request, urllib.error

if len(sys.argv) < 2:
    print("用法: python _deploy.py <github_token>")
    sys.exit(1)

TOKEN = sys.argv[1].strip()
REPO = "img-crop-tool"
SRC = os.path.dirname(os.path.abspath(__file__))

H = {
    "User-Agent": "workbuddy-deploy",
    "Authorization": "token " + TOKEN,
    "Accept": "application/vnd.github+json",
}


def req(method, url, data=None, timeout=90):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    r = urllib.request.Request(url, data=body, headers=H, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f:
            raw = f.read().decode("utf-8", "replace")
            return f.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:400]}
    except Exception as e:
        return -1, {"raw": str(e)}


def git(*args, check=True):
    p = subprocess.run(["git"] + list(args), cwd=SRC,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        print("git", " ".join(args), "失败:", p.stdout, p.stderr)
        sys.exit(1)
    return p


# 1) 确认身份
st, me = req("GET", "https://api.github.com/user")
if st != 200:
    print("token 无效或无法访问 GitHub API:", st, me)
    sys.exit(1)
owner = me.get("login")
print("GitHub 账号:", owner)

# 2) 建仓库（已存在就复用）
st, res = req("POST", "https://api.github.com/user/repos",
              {"name": REPO, "private": False, "auto_init": False, "description": "图片统一裁剪工具"})
if st == 201:
    print("仓库已创建:", REPO)
elif st == 422:
    print("仓库已存在，直接复用:", REPO)
else:
    print("创建仓库失败:", st, res)
    sys.exit(1)

# 3) 提交并推送
if not os.path.exists(os.path.join(SRC, ".git")):
    git("init")
git("config", "user.email", "deploy@example.com")
git("config", "user.name", owner or "deploy")
git("add", "-A")
git("commit", "-m", "update site", check=False)
git("branch", "-M", "main")
remote_url = "https://%s@github.com/%s/%s.git" % (TOKEN, owner, REPO)
git("remote", "remove", "origin", check=False)
git("remote", "add", "origin", remote_url)
p = git("push", "-u", "-f", "origin", "main", check=False)
if p.returncode != 0:
    print("推送失败:", p.stdout[-800:], p.stderr[-800:])
    sys.exit(1)
print("代码已推送")

# 4) 开启 Pages
st, res = req("POST", "https://api.github.com/repos/%s/%s/pages" % (owner, REPO),
              {"source": {"branch": "main", "path": "/"}})
if st in (201, 204, 409):
    print("Pages 已开启")
else:
    print("开启 Pages 返回:", st, res)

# 5) 取链接
url = None
for _ in range(20):
    st, info = req("GET", "https://api.github.com/repos/%s/%s/pages" % (owner, REPO))
    if st == 200 and info.get("html_url"):
        url = info["html_url"]
        break
    time.sleep(6)
if not url:
    url = "https://%s.github.io/%s/" % (owner, REPO)
print("SHARE_URL:", url)
