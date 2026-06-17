import json
import os
import shutil
import sqlite3
import uuid
import zipfile
from datetime import datetime, date, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR)).resolve()
DB_PATH = DATA_DIR / "nuvem.db"
UPLOAD_ROOT = DATA_DIR / "uploads"
PHOTO_DIR = UPLOAD_ROOT / "fotos"
VIDEO_DIR = UPLOAD_ROOT / "videos"
THUMB_DIR = UPLOAD_ROOT / "thumbs"
BACKUP_DIR = DATA_DIR / "backups"
RESTORE_TMP_DIR = DATA_DIR / ".restore_tmp"
ALLOWED_PHOTOS = {"jpg", "jpeg", "png", "gif", "webp", "heic", "heif"}
ALLOWED_VIDEOS = {"mp4", "mov", "webm", "avi", "mkv", "m4v"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")


def ensure_storage():
    for folder in (PHOTO_DIR, VIDEO_DIR, THUMB_DIR, BACKUP_DIR):
        folder.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS arquivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_arquivo TEXT NOT NULL,
                caminho TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('foto', 'video')),
                data_upload TEXT NOT NULL,
                usuario TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sistema (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
            """
        )
        conn.commit()


ensure_storage()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("usuario"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def configured_user():
    return os.environ.get("NUVEM_USUARIO", "admin")


def configured_password_hash():
    password_hash = os.environ.get("NUVEM_SENHA_HASH")
    if password_hash:
        return password_hash
    dev_password = os.environ.get("NUVEM_SENHA_DEV", "admin123")
    return generate_password_hash(dev_password)


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def date_bounds(day):
    start = datetime.combine(day, datetime.min.time())
    end = start + timedelta(days=1)
    return start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds")


def list_files(kind="todas", day=None):
    where = ["usuario = ?"]
    params = [session["usuario"]]
    if kind in {"foto", "video"}:
        where.append("tipo = ?")
        params.append(kind)
    if day:
        start, end = date_bounds(day)
        where.append("data_upload >= ? AND data_upload < ?")
        params.extend([start, end])
    rows = get_db().execute(
        f"SELECT * FROM arquivos WHERE {' AND '.join(where)} ORDER BY data_upload DESC",
        params,
    ).fetchall()
    grouped = {}
    for row in rows:
        label = datetime.fromisoformat(row["data_upload"]).strftime("%d/%m/%Y")
        grouped.setdefault(label, []).append(row)
    return grouped


def system_get(key, default=None):
    row = get_db().execute("SELECT valor FROM sistema WHERE chave = ?", (key,)).fetchone()
    return row["valor"] if row else default


def system_set(key, value):
    get_db().execute(
        "INSERT INTO sistema (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
        (key, value),
    )
    get_db().commit()


def backup_status():
    last = system_get("ultimo_backup")
    return {"ultimo_backup": last.replace("T", " ") if last else "Nunca", "arquivo": system_get("ultimo_backup_arquivo")}


def add_path_to_zip(zipf, path, arcname):
    if path.is_file():
        zipf.write(path, arcname.as_posix())
    elif path.is_dir():
        zipf.writestr(f"{arcname.as_posix().rstrip('/')}/", "")
        for item in path.rglob("*"):
            relative_name = item.relative_to(DATA_DIR).as_posix()
            if item.is_dir():
                zipf.writestr(f"{relative_name.rstrip('/')}/", "")
            elif item.is_file():
                zipf.write(item, relative_name)


def create_cloud_export(prefix="backup"):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_path = BACKUP_DIR / f"{prefix}-{stamp}.zip"
    manifest = {
        "app": "nuvem_pessoal",
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "inclui": ["fotos", "videos", "banco de dados", "metadados"],
        "versao_exportacao": 1,
    }
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        add_path_to_zip(zipf, PHOTO_DIR, Path("uploads/fotos"))
        add_path_to_zip(zipf, VIDEO_DIR, Path("uploads/videos"))
        add_path_to_zip(zipf, THUMB_DIR, Path("uploads/thumbs"))
        if DB_PATH.exists():
            zipf.write(DB_PATH, "nuvem.db")
        zipf.writestr("metadata/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    system_set("ultimo_backup", manifest["criado_em"])
    system_set("ultimo_backup_arquivo", zip_path.name)
    return zip_path


def maybe_run_daily_backup():
    ensure_storage()
    last = system_get("ultimo_backup")
    if not last or datetime.fromisoformat(last).date() < date.today():
        create_cloud_export("backup-diario")


def latest_backup_file():
    saved = system_get("ultimo_backup_arquivo")
    if saved and (BACKUP_DIR / saved).exists():
        return BACKUP_DIR / saved
    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return backups[0] if backups else None


def safe_extract(zip_path, target):
    with zipfile.ZipFile(zip_path) as zipf:
        for member in zipf.infolist():
            destination = (target / member.filename).resolve()
            if not str(destination).startswith(str(target.resolve())):
                raise ValueError("ZIP inválido: caminho inseguro.")
        zipf.extractall(target)


def restore_cloud_export(zip_path):
    if RESTORE_TMP_DIR.exists():
        shutil.rmtree(RESTORE_TMP_DIR)
    RESTORE_TMP_DIR.mkdir(parents=True)
    safe_extract(zip_path, RESTORE_TMP_DIR)
    restored_db = RESTORE_TMP_DIR / "nuvem.db"
    restored_uploads = RESTORE_TMP_DIR / "uploads"
    if not restored_db.exists() or not restored_uploads.exists():
        raise ValueError("ZIP inválido: exportação deve conter nuvem.db e uploads/.")
    safety = create_cloud_export("antes-da-importacao")
    db = g.pop("db", None)
    if db is not None:
        db.close()
    if UPLOAD_ROOT.exists():
        shutil.rmtree(UPLOAD_ROOT)
    shutil.copytree(restored_uploads, UPLOAD_ROOT)
    shutil.copy2(restored_db, DB_PATH)
    shutil.rmtree(RESTORE_TMP_DIR)
    ensure_storage()
    return safety


def media_type(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ALLOWED_PHOTOS:
        return "foto"
    if ext in ALLOWED_VIDEOS:
        return "video"
    return None


@app.before_request
def automatic_daily_backup():
    if request.endpoint not in {"static", "media", "download", "download_backup"}:
        maybe_run_daily_backup()


@app.route("/")
def index():
    return redirect(url_for("gallery_all") if session.get("usuario") else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        if usuario == configured_user() and check_password_hash(configured_password_hash(), senha):
            session.clear()
            session["usuario"] = usuario
            return redirect(request.args.get("next") or url_for("gallery_all"))
        flash("Usuário ou senha inválidos.", "erro")
    return render_template("login.html")


@app.post("/sair")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/todas-as-fotos")
@login_required
def gallery_all():
    filtro = request.args.get("filtro", "todas")
    kind = filtro if filtro in {"foto", "video"} else "todas"
    return render_template("gallery.html", grupos=list_files(kind=kind), titulo="Todas as fotos e vídeos", filtro=filtro, data_pesquisa="")


@app.route("/fotos/hoje")
@login_required
def gallery_today():
    return render_template("gallery.html", grupos=list_files(day=date.today()), titulo="Fotos e vídeos de hoje", filtro="hoje", data_pesquisa=date.today().strftime("%d/%m/%Y"))


@app.route("/fotos/ontem")
@login_required
def gallery_yesterday():
    yesterday = date.today() - timedelta(days=1)
    return render_template("gallery.html", grupos=list_files(day=yesterday), titulo="Fotos e vídeos de ontem", filtro="ontem", data_pesquisa=yesterday.strftime("%d/%m/%Y"))


@app.route("/fotos/data/<data>")
@login_required
def gallery_by_date(data):
    parsed = parse_date(data)
    if not parsed:
        abort(404)
    return render_template("gallery.html", grupos=list_files(day=parsed), titulo=f"Arquivos de {parsed.strftime('%d/%m/%Y')}", filtro="data", data_pesquisa=parsed.strftime("%d/%m/%Y"))


@app.route("/pesquisar")
@login_required
def search():
    data = request.args.get("data", "")
    parsed = parse_date(data)
    if data and parsed:
        return render_template("gallery.html", grupos=list_files(day=parsed), titulo=f"Resultado para {parsed.strftime('%d/%m/%Y')}", filtro="pesquisa", data_pesquisa=data)
    if data:
        flash("Use uma data nos formatos 10/06/2026 ou 10-06-2026.", "erro")
    return render_template("gallery.html", grupos={}, titulo="Pesquisar por data", filtro="pesquisa", data_pesquisa=data)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        files = request.files.getlist("arquivo")
        saved = 0
        for file in files:
            if not file or not file.filename:
                continue
            safe = secure_filename(file.filename)
            kind = media_type(safe)
            if not kind:
                flash(f"Tipo não aceito: {safe}", "erro")
                continue
            ext = safe.rsplit(".", 1)[-1].lower()
            unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex}.{ext}"
            folder = PHOTO_DIR if kind == "foto" else VIDEO_DIR
            path = folder / unique_name
            file.save(path)
            rel_path = path.relative_to(DATA_DIR).as_posix()
            get_db().execute(
                "INSERT INTO arquivos (nome_arquivo, caminho, tipo, data_upload, usuario) VALUES (?, ?, ?, ?, ?)",
                (unique_name, rel_path, kind, datetime.now().isoformat(timespec="seconds"), session["usuario"]),
            )
            saved += 1
        get_db().commit()
        flash(f"{saved} arquivo(s) enviado(s) com sucesso.", "ok")
        return redirect(url_for("gallery_all"))
    return render_template("upload.html")


@app.route("/media/<int:file_id>")
@login_required
def media(file_id):
    row = get_db().execute("SELECT * FROM arquivos WHERE id = ? AND usuario = ?", (file_id, session["usuario"])).fetchone()
    if not row:
        abort(404)
    path = DATA_DIR / row["caminho"]
    return send_from_directory(path.parent, path.name)


@app.route("/baixar/<int:file_id>")
@login_required
def download(file_id):
    row = get_db().execute("SELECT * FROM arquivos WHERE id = ? AND usuario = ?", (file_id, session["usuario"])).fetchone()
    if not row:
        abort(404)
    path = DATA_DIR / row["caminho"]
    return send_from_directory(path.parent, path.name, as_attachment=True, download_name=row["nome_arquivo"])


@app.route("/configuracoes")
@login_required
def settings():
    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return render_template("settings.html", titulo="Configurações", status=backup_status(), backups=backups)


@app.get("/exportar")
@login_required
def export_cloud():
    path = create_cloud_export("exportacao-nuvem")
    flash("Exportação completa criada com sucesso.", "ok")
    return send_file(path, as_attachment=True, download_name=path.name)


@app.post("/importar")
@login_required
def import_cloud():
    file = request.files.get("backup")
    if not file or not file.filename:
        flash("Selecione um arquivo ZIP de exportação.", "erro")
        return redirect(url_for("settings"))
    if not file.filename.lower().endswith(".zip"):
        flash("Envie um arquivo .zip válido.", "erro")
        return redirect(url_for("settings"))
    temp = BACKUP_DIR / f"importacao-{uuid.uuid4().hex}.zip"
    file.save(temp)
    try:
        safety = restore_cloud_export(temp)
        flash(f"Nuvem importada com sucesso. Backup de segurança salvo em {safety.name}.", "ok")
    except Exception as exc:
        flash(str(exc), "erro")
    finally:
        if temp.exists():
            temp.unlink()
    return redirect(url_for("settings"))


@app.post("/backup-agora")
@login_required
def backup_now():
    path = create_cloud_export("backup-manual")
    flash(f"Backup criado: {path.name}", "ok")
    return redirect(url_for("settings"))


@app.get("/backup/baixar")
@login_required
def download_backup():
    path = latest_backup_file()
    if not path:
        flash("Nenhum backup disponível para baixar.", "erro")
        return redirect(url_for("settings"))
    return send_file(path, as_attachment=True, download_name=path.name)


@app.post("/excluir/<int:file_id>")
@login_required
def delete(file_id):
    row = get_db().execute("SELECT * FROM arquivos WHERE id = ? AND usuario = ?", (file_id, session["usuario"])).fetchone()
    if not row:
        abort(404)
    path = DATA_DIR / row["caminho"]
    if path.exists():
        path.unlink()
    get_db().execute("DELETE FROM arquivos WHERE id = ? AND usuario = ?", (file_id, session["usuario"]))
    get_db().commit()
    flash("Arquivo excluído.", "ok")
    return redirect(request.referrer or url_for("gallery_all"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
