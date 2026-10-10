import os
from pathlib import Path

import requests

from checks import imprimir
from checks import verificar
from code import extrair_texto

pasta = Path(__file__).resolve().parent
caminho_prompt = pasta / "prompt.txt"
caminho_saida = pasta / "submission.txt"
caminho_env = pasta.parent / ".env"

MODELO = "gemini-2.0-flash"
URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODELO
    + ":generateContent"
)


def ler_env(caminho):
    if not caminho.is_file():
        return
    texto = caminho.read_text(encoding="utf-8")
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)
        nome = nome.strip()
        valor = valor.strip().strip('"').strip("'")
        if nome and nome not in os.environ:
            os.environ[nome] = valor


def chave_api():
    ler_env(caminho_env)
    for nome in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "API_KEY"):
        valor = os.environ.get(nome, "").strip()
        if valor:
            return valor
    raise SystemExit(
        "Chave em falta. Define GEMINI_API_KEY no ficheiro .env da raiz."
    )


def gerar_texto(prompt_text, api_key):
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0
        }
    }
    response = requests.post(URL, headers=headers, json=body, timeout=120)
    if not response.ok:
        estado = str(response.status_code)
        raise SystemExit("A API Gemini devolveu o estado " + estado + ".")
    dados = response.json()
    try:
        return dados["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise SystemExit("A API Gemini não devolveu texto.")


def prompt_completo(instrucoes, documento):
    if "{{DOCUMENTO}}" in instrucoes:
        return instrucoes.replace("{{DOCUMENTO}}", documento)
    return instrucoes + "\n\nDocumento:\n" + documento


def main():
    instrucoes = caminho_prompt.read_text(encoding="utf-8").strip()
    if not instrucoes:
        raise SystemExit(
            "submission/prompt.txt está vazio. "
            "O prompt tem de estar escrito antes da chamada."
        )
    texto = extrair_texto()
    resposta = gerar_texto(
        prompt_completo(instrucoes, texto),
        chave_api(),
    ).strip()
    caminho_saida.write_text(resposta + "\n", encoding="utf-8")
    print("Escrito submission/submission.txt")
    imprimir(verificar(resposta))


if __name__ == "__main__":
    main()
