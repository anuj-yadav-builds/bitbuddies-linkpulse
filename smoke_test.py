"""
Checks the whole LinkPulse app like a real visitor would use it.

  python smoke_test.py                                    (tests your laptop)
  python smoke_test.py https://bitbuddies-linkpulse.onrender.com   (tests the live site)
  python smoke_test.py <address> <admin-email> <admin-password>    (also tests the Admin page)

No extra install needed. Start the server first when testing locally.
It creates one temporary test user and a few test links (their codes start with "smoke").
"""
import http.cookiejar
import json
import random
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/")
BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow redirects, so we can look at the 302 itself."""
    def redirect_request(self, *args, **kwargs):
        return None


jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(jar))
results = []


def call(method, path, form=None, raw=None, content_type=None):
    data = raw
    headers = {"User-Agent": BROWSER}
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with opener.open(req, timeout=90) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read().decode("utf-8", "replace")


def csrf_from(path):
    status, _, body = call("GET", path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', body)
    return match.group(1) if match else ""


def check(name, ok, extra=""):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name + (f"   ({extra})" if extra and not ok else ""))


def new_link(token, url, alias, **more):
    form = {"csrf_token": token, "url": url, "alias": alias, "expires": "",
            "click_limit": "", "password": "", "campaign": "", "tags": ""}
    form.update(more)
    return call("POST", "/links/new", form)


print(f"Testing {BASE}\n(first call can take ~1 minute if the live site was sleeping)\n")

status, _, body = call("GET", "/health")
check("1. Health check - database connected", status == 200 and "connected" in body, body[:150])

token = csrf_from("/login")
check("2. Login page opens", bool(token))

tag = str(random.randint(10000, 99999))
email = f"smoke{tag}@example.com"
status, headers, _ = call("POST", "/register", {"csrf_token": token, "name": "Smoke Tester",
                                                "email": email, "password": "secret123"})
check("3. Register a new account", status == 302 and "/login" in headers.get("Location", ""),
      str(status))

status, headers, _ = call("POST", "/login", {"csrf_token": token, "email": email,
                                             "password": "wrong-password"})
check("4. Wrong password is refused", status == 200, str(status))

status, headers, _ = call("POST", "/login", {"csrf_token": token, "email": email,
                                             "password": "secret123"})
check("5. Login works", status == 302, f"{status} {headers.get('Location')}")

status, _, body = call("GET", "/")
check("6. Dashboard opens", status == 200 and "Analytics Dashboard" in body, str(status))

token = csrf_from("/links/new")
alias = "smoke" + tag
status, _, body = call("GET", f"/api/check-alias?alias={alias}")
check("7. Alias check says available", status == 200 and json.loads(body)["available"], body[:100])

status, headers, _ = new_link(token, "https://www.wikipedia.org", alias, tags="smoke, test")
check("8. Create a short link", status == 302 and f"/links/{alias}" in headers.get("Location", ""),
      f"{status} {headers.get('Location')}")

status, headers, _ = new_link(token, "https://example.com", alias)
check("9. Same alias again is refused", status == 302 and "/links/new" in headers.get("Location", ""),
      f"{status} {headers.get('Location')}")

status, headers, _ = new_link(token, "javascript:alert(1)", "smokebad" + tag)
check("10. Dangerous link is refused", status == 302 and "/links/new" in headers.get("Location", ""),
      f"{status} {headers.get('Location')}")

status, _, body = call("GET", f"/links/{alias}")
check("11. Link detail page opens", status == 200 and alias in body, str(status))

status, headers, _ = call("GET", f"/{alias}")
check("12. Short link redirects (302)",
      status == 302 and "wikipedia.org" in headers.get("Location", ""), f"{status}")

status, _, body = call("GET", f"/links/{alias}/analytics")
check("13. Analytics page opens", status == 200 and "Analytics for" in body and "Chrome" in body,
      str(status))

# password protected link
pw_alias = "smokepw" + tag
new_link(token, "https://example.org", pw_alias, password="abc123")
status, _, body = call("GET", f"/{pw_alias}")
check("14. Protected link asks for a password", status == 200 and "protected" in body, str(status))
pw_token = csrf_from(f"/{pw_alias}")
status, _, body = call("POST", f"/{pw_alias}", {"csrf_token": pw_token, "password": "nope"})
check("15. Wrong link password is refused", status == 200 and "Wrong password" in body, str(status))
status, headers, _ = call("POST", f"/{pw_alias}", {"csrf_token": pw_token, "password": "abc123"})
check("16. Right link password redirects", status == 302 and "example.org" in headers.get("Location", ""),
      str(status))

# click limit
lim_alias = "smokelim" + tag
new_link(token, "https://example.net", lim_alias, click_limit="1")
first, _, _ = call("GET", f"/{lim_alias}")
second, _, body = call("GET", f"/{lim_alias}")
check("17. Click limit stops the 2nd click", first == 302 and second == 410 and "limit" in body.lower(),
      f"{first}/{second}")

# campaign
camp = "Smoke Campaign " + tag
call("POST", "/campaigns/new", {"csrf_token": token, "name": camp})
status, _, body = call("GET", "/campaigns")
check("18. Campaign is created and listed", status == 200 and camp in body, str(status))

# bulk import
boundary = "----smoke" + tag
csv_text = f"url,alias\nhttps://example.com/a,smokeimp{tag}\nnot-a-url,beta\nhttps://example.com/d,login\n"
payload = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"csrf_token\"\r\n\r\n{token}\r\n"
           f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"t.csv\"\r\n"
           f"Content-Type: text/csv\r\n\r\n{csv_text}\r\n--{boundary}--\r\n").encode()
status, _, body = call("POST", "/import", raw=payload,
                       content_type=f"multipart/form-data; boundary={boundary}")
check("19. Bulk import: 1 imported, 2 skipped",
      status == 200 and "1 imported, 2 skipped" in body, str(status))

status, _, _ = call("GET", "/zzzzzz")
check("20. Unknown short link gives 404", status == 404, str(status))

status, headers, _ = call("GET", "/logout")
status2, headers2, _ = call("GET", "/")
check("21. Logout, then the dashboard needs login again",
      status == 302 and status2 == 302 and "/login" in headers2.get("Location", ""),
      f"{status}/{status2}")


def sign_in(mail, password):
    tok = csrf_from("/login")
    return call("POST", "/login", {"csrf_token": tok, "email": mail, "password": password})


# a second, normal user must not see the first user's link or the Admin page
email2 = f"smoke{tag}b@example.com"
tok = csrf_from("/login")
call("POST", "/register", {"csrf_token": tok, "name": "Second Tester", "email": email2,
                           "password": "secret123"})
sign_in(email2, "secret123")
status, _, _ = call("GET", f"/links/{alias}")
check("22. Another user cannot open my link (404)", status == 404, str(status))
status, headers, _ = call("GET", "/admin")
check("23. Normal user cannot open Admin", status == 302, str(status))
call("GET", "/logout")

# optional: admin checks (only when an admin email and password are given)
if len(sys.argv) >= 4:
    status, headers, _ = sign_in(sys.argv[2], sys.argv[3])
    check("24. Admin login works", status == 302, f"{status} {headers.get('Location')}")
    status, _, body = call("GET", "/admin")
    check("25. Admin page opens and lists links", status == 200 and alias in body, str(status))
    atoken = csrf_from("/links/new")
    adm = "smokeadm" + tag
    new_link(atoken, "https://example.com/admin-test", adm)
    call("POST", f"/links/{adm}/toggle", {"csrf_token": atoken})
    status, _, body = call("GET", f"/{adm}")
    check("26. Disabled link shows the disabled page (403)",
          status == 403 and "disabled" in body.lower(), str(status))
    call("POST", f"/links/{adm}/toggle", {"csrf_token": atoken})
    status, _, _ = call("GET", f"/{adm}")
    check("27. Re-enabled link redirects again", status == 302, str(status))
    bad = f"smoke-blocked-{tag}.com"
    call("POST", "/admin/blocklist", {"csrf_token": atoken, "domain": bad})
    status, _, body = call("GET", "/api/check-url?url=" + urllib.parse.quote(f"https://{bad}/x"))
    check("28. Blocked domain is marked unsafe", status == 200 and '"safe":false' in body.replace(" ", ""),
          body[:100])
    status, headers, _ = new_link(atoken, f"https://{bad}/x", "smokeblk" + tag)
    check("29. Link to a blocked domain is refused",
          status == 302 and "/links/new" in headers.get("Location", ""), str(status))
    call("GET", "/logout")

print(f"\n{sum(results)} of {len(results)} checks passed.")
print("Test data: user", email, "and links starting with 'smoke' (delete them before the demo).")
sys.exit(0 if all(results) else 1)
