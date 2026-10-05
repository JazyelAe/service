"""BiblioServ - Servicio REST para administrar libros de una biblioteca escolar."""
import secrets, sqlite3
from functools import wraps
from flask import Flask, g, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="static")
DB = "biblioteca.db"
USUARIOS = {"bibliotecario": "demo1234"}
TOKENS = {}

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def cerrar(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS libros(
        id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL,
        autor TEXT NOT NULL, disponible INTEGER NOT NULL DEFAULT 1)""")
    if c.execute("SELECT COUNT(*) FROM libros").fetchone()[0] == 0:
        c.executemany("INSERT INTO libros(titulo, autor, disponible) VALUES (?,?,?)", [
            ("Cien años de soledad", "Gabriel García Márquez", 1),
            ("El laberinto de la soledad", "Octavio Paz", 1),
            ("Pedro Páramo", "Juan Rulfo", 0),
            ("Como agua para chocolate", "Laura Esquivel", 1),
            ("La muerte de Artemio Cruz", "Carlos Fuentes", 1)])
        c.commit()
    c.close()

def requiere_token(f):
    @wraps(f)
    def w(*a, **k):
        t = request.headers.get("Authorization", "").replace("Token ", "")
        if t not in TOKENS:
            return jsonify(error="Token inválido o ausente"), 401
        g.usuario = TOKENS[t]
        return f(*a, **k)
    return w

@app.post("/api/login/")
def login():
    d = request.get_json(force=True)
    if USUARIOS.get(d.get("usuario")) != d.get("password"):
        return jsonify(error="Credenciales incorrectas"), 400
    t = secrets.token_hex(16); TOKENS[t] = d["usuario"]
    return jsonify(usuario=d["usuario"], token=t)

@app.get("/api/perfil/")
@requiere_token
def perfil():
    return jsonify(usuario=g.usuario, rol="Bibliotecario")

@app.get("/api/libros/")
@requiere_token
def listar():
    return jsonify([dict(r) for r in db().execute("SELECT * FROM libros ORDER BY id")])

@app.post("/api/libros/")
@requiere_token
def crear():
    d = request.get_json(force=True)
    cur = db().execute("INSERT INTO libros(titulo, autor) VALUES (?,?)", (d["titulo"], d["autor"]))
    db().commit()
    return jsonify(id=cur.lastrowid, titulo=d["titulo"], autor=d["autor"], disponible=1), 201

@app.put("/api/libros/<int:i>/")
@requiere_token
def actualizar(i):
    d = request.get_json(force=True)
    db().execute("UPDATE libros SET disponible=? WHERE id=?", (1 if d.get("disponible") else 0, i))
    db().commit()
    return jsonify(id=i, disponible=1 if d.get("disponible") else 0)

@app.delete("/api/libros/<int:i>/")
@requiere_token
def borrar(i):
    db().execute("DELETE FROM libros WHERE id=?", (i,)); db().commit()
    return "", 204

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

if __name__ == "__main__":
    init_db()
    app.run(port=5000)
