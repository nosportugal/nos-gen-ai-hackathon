import re
from pathlib import Path

pasta = Path(__file__).resolve().parent
caminho_saida = pasta / "submission.txt"

LINHAS_OBRIGATORIAS = (
    "Relatório de Admissão - Centro Médico Lisboa",
    "Data: 15 de abril de 2025",
    "Referência: ADM-2025-04-15-089",
    "Informações do Paciente:",
)

EMAIL = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
TELEFONE = re.compile(
    r"(?:\+351[\s.-]?)?(?:9[1236]\d{7}|2\d{8})\b"
)
NIF = re.compile(r"\b[1-9]\d{8}\b")
ASTERISCOS = re.compile(r"\*{2,}")


def verificar(texto):
    problemas = []

    for linha in LINHAS_OBRIGATORIAS:
        if linha not in texto:
            problemas.append("Falta no texto: " + linha)

    for numero, linha in enumerate(texto.splitlines(), start=1):
        if linha.strip() == "":
            problemas.append("Linha vazia na linha " + str(numero))

    for email in EMAIL.findall(texto):
        problemas.append("Email ainda visível: " + email)

    for telefone in TELEFONE.findall(texto):
        problemas.append("Telefone ainda visível: " + telefone)

    for nif in NIF.findall(texto):
        problemas.append("NIF ainda visível: " + nif)

    for asteriscos in ASTERISCOS.findall(texto):
        problemas.append(
            "Vários asteriscos juntos: " + asteriscos
            + ". Cada palavra mascarada é um só *."
        )

    return problemas


def imprimir(problemas):
    if not problemas:
        print("Verificador: nada a apontar.")
        return
    print("Verificador: o prompt precisa de correção.")
    for item in problemas:
        print("- " + item)


def main():
    if not caminho_saida.is_file():
        raise SystemExit("submission/submission.txt não existe.")
    texto = caminho_saida.read_text(encoding="utf-8")
    problemas = verificar(texto)
    imprimir(problemas)
    if problemas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
