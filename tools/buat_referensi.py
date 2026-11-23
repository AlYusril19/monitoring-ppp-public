"""Buat ulang docs/REFERENSI-MODUL.md dari kode (docstring & tanda tangan fungsi).

    python tools/buat_referensi.py

Jalankan setiap kali menambah/mengubah fungsi. Penjelasan diambil dari baris
pertama docstring, jadi tulis docstring singkat untuk setiap fungsi baru.
"""
import ast
import datetime
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "docs", "REFERENSI-MODUL.md")
SECTIONS = {
    "main.py": "Entry point",
    "configs": "configs/ — layanan (data, pengaturan, billing, Telegram, MikroTik)",
    "handlers": "handlers/ — fitur Telegram (menu, form, monitoring)",
    "models": "models/ — sesi di memori",
}


def _signature(node):
    args = node.args
    parts = [a.arg for a in args.args]
    if args.vararg:
        parts.append("*" + args.vararg.arg)
    parts += [a.arg for a in args.kwonlyargs]
    if args.kwarg:
        parts.append("**" + args.kwarg.arg)
    return f"{node.name}({', '.join(parts)})"


def _first_line(doc):
    return (doc or "").strip().split("\n")[0].strip().replace("|", "/") or "—"


def build():
    os.chdir(ROOT)
    files = ["main.py"] + sorted(glob.glob("configs/*.py")) + sorted(glob.glob("handlers/*.py")) + \
        sorted(glob.glob("models/*.py"))
    out = ["# Referensi Modul", "",
           f"> Dibuat otomatis oleh `tools/buat_referensi.py` pada {datetime.date.today():%d/%m/%Y}. "
           "Jangan diedit manual: ubah docstring di kode lalu jalankan ulang.",
           "> Fungsi berawalan `_` adalah internal modul. Alur & aturan: [`ARSITEKTUR.md`](ARSITEKTUR.md).", ""]
    current = None
    for path in (f.replace("\\", "/") for f in files):  # Windows glob uses backslashes
        tree = ast.parse(open(path, encoding="utf-8").read())
        if not tree.body:
            continue  # file kosong
        group = path.split("/")[0] if "/" in path else path
        if group != current:
            out += [f"## {SECTIONS[group]}", ""]
            current = group
        out.append(f"### `{path}`")
        doc = ast.get_docstring(tree)
        if doc:
            out.append(_first_line(doc))
        out.append("")
        constants = [n.targets[0].id for n in tree.body if isinstance(n, ast.Assign)
                     and isinstance(n.targets[0], ast.Name) and n.targets[0].id.isupper()]
        if constants:
            out += ["Konstanta: " + ", ".join(f"`{c}`" for c in constants), ""]
        rows = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                rows.append(f"| `{_signature(node)}` | {_first_line(ast.get_docstring(node))} |")
            elif isinstance(node, ast.ClassDef):
                rows.append(f"| class `{node.name}` | {_first_line(ast.get_docstring(node))} |")
                for member in node.body:
                    if isinstance(member, ast.FunctionDef) and not member.name.startswith("__"):
                        rows.append(f"| &nbsp;&nbsp;`.{_signature(member)}` | "
                                    f"{_first_line(ast.get_docstring(member))} |")
        if rows:
            out += ["| Fungsi | Keterangan |", "|---|---|"] + rows + [""]
    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write("\n".join(out))
    print(f"Ditulis: {OUTPUT}")


if __name__ == "__main__":
    build()
