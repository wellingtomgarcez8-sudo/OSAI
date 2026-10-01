from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from osai.ai.planner import build_spec
from osai.generator.compiler import compile_project
from osai.validation.project import validate_project

app = FastAPI(title="OSAI", version="0.1.0")

INDEX = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OSAI</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,sans-serif;background:#090b12;color:#f8fafc;min-height:100vh}
main{max-width:920px;margin:0 auto;padding:56px 24px}.hero{padding:30px;border:1px solid #292b3b;background:linear-gradient(160deg,#141627,#0b0d15);border-radius:26px;box-shadow:0 20px 60px #0008}
h1{font-size:48px;margin:0 0 8px;background:linear-gradient(90deg,#b794f6,#7c3aed);-webkit-background-clip:text;color:transparent}p{color:#aeb5c5;line-height:1.6}label{display:block;margin:18px 0 7px;font-weight:700}input,textarea{width:100%;border:1px solid #34374d;background:#0e1019;color:white;border-radius:14px;padding:14px;font:inherit}textarea{min-height:190px;resize:vertical}button{margin-top:20px;border:0;border-radius:14px;padding:14px 22px;font-weight:800;background:#7c3aed;color:white;cursor:pointer}code{color:#c4b5fd}.small{font-size:13px}</style></head>
<body><main><section class="hero"><h1>OSAI</h1><p>Descreva o sistema operacional. Envie imagens de referência. OSAI cria um projeto Linux reproduzível, valida os arquivos e prepara a build da ISO sem usar API de outra IA.</p>
<form action="/api/create" method="post" enctype="multipart/form-data"><label>Nome do OS</label><input name="name" value="MyOS" required><label>Prompt</label><textarea name="prompt" required placeholder="Ex.: sistema gamer smooth, KDE, dark mode roxo, Steam, Wine..."></textarea><label>Imagens de referência</label><input type="file" name="references" accept="image/*" multiple><label>Pasta de saída no host</label><input name="output" value="./work"><button type="submit">Gerar projeto</button></form><p class="small">A ISO só é construída quando você executar <code>osai build CAMINHO_DO_PROJETO</code>, após a validação.</p></section></main></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX


@app.post("/api/create")
async def create(
    name: str = Form(...),
    prompt: str = Form(...),
    output: str = Form("./work"),
    references: list[UploadFile] = File(default=[]),
):
    temp_root = Path(tempfile.mkdtemp(prefix="osai-refs-"))
    saved: list[Path] = []
    try:
        for upload in references:
            if not upload.filename:
                continue
            target = temp_root / Path(upload.filename).name
            with target.open("wb") as fp:
                shutil.copyfileobj(upload.file, fp)
            saved.append(target)
        spec = build_spec(name, prompt, saved)
        project = compile_project(spec, Path(output).expanduser().resolve())
        result = validate_project(project)
        status = 200 if result.ok else 400
        return JSONResponse(
            {
                "ok": result.ok,
                "project": str(project),
                "errors": result.errors,
                "warnings": result.warnings,
                "next": f"osai build {project}",
            },
            status_code=status,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
