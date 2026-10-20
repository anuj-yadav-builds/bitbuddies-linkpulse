"""Bulk import of links from a CSV file (columns: url,alias)."""
import csv
import io

from flask import flash, g, redirect, render_template, request, url_for

from services import create_link, login_required

MAX_ROWS = 500


def add_import_views(app):

    @app.route("/import", methods=["GET", "POST"])
    @login_required
    def bulk_import():
        report = None
        if request.method == "POST":
            upload = request.files.get("file")
            if not upload or not upload.filename:
                flash("Please choose a CSV file.", "danger")
                return redirect(url_for("bulk_import"))

            text = upload.read().decode("utf-8-sig", errors="replace")
            rows, imported = [], 0
            for n, row in enumerate(csv.DictReader(io.StringIO(text)), start=1):
                if n > MAX_ROWS:
                    flash(f"Only the first {MAX_ROWS} rows were checked.", "warning")
                    break
                url = (row.get("url") or "").strip()
                alias = (row.get("alias") or "").strip().lower()

                if not url.startswith(("http://", "https://")):
                    result, code = "Invalid URL", None
                else:
                    link, error = create_link(g.user, url=url, alias=alias)
                    if error:
                        result, code = error, None
                    else:
                        result, code = "Imported", link.code
                ok = result == "Imported"
                imported += 1 if ok else 0
                rows.append({"n": n, "url": url, "alias": code or alias or "-",
                             "result": result, "ok": ok})
            report = {"rows": rows, "imported": imported, "skipped": len(rows) - imported}
        return render_template("import.html", report=report)
