import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from checks import imprimir
from checks import verificar
from code import extrair_texto

pasta = Path(__file__).resolve().parent
caminho_prompt = pasta / "prompt.txt"
caminho_saida = pasta / "submission.txt"

MODELO = "gemini-3.8-flash"
URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    + MODELO
    + ":generateContent"
)


def chave_api():
    load_dotenv(pasta.parent / ".env")
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
            "thinkingConfig": {
                "thinkingLevel": "low"
            }
        },
    }
    try:
        response = requests.post(
            URL, headers=headers, json=body, timeout=300
        )
    except requests.Timeout:
        raise SystemExit(
            "A API Gemini não respondeu a tempo. Volta a correr o comando."
        )
    if not response.ok:
        estado = str(response.status_code)
        raise SystemExit("A API Gemini devolveu o estado " + estado + ".")
    dados = response.json()
    try:
        partes = dados["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        raise SystemExit("A API Gemini não devolveu texto.")
    textos = []
    for parte in partes:
        if parte.get("thought"):
            continue
        if "text" in parte:
            textos.append(parte["text"])
    if not textos:
        raise SystemExit("A API Gemini não devolveu texto.")
    return textos[-1]


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
