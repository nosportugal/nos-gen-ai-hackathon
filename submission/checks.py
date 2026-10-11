import re
from pathlib import Path

pasta = Path(__file__).resolve().parent
caminho_saida = pasta / "submission.txt"

LINHAS_OBRIGATORIAS = (
    "Relatório de Admissão - Centro Médico Lisboa",
    "Data: 15 de abril de 2025",
    "Referência: ADM-2025-04-15-089",
    "Informações do Paciente:",
    "Especialidade: Medicina Interna",
)

PROIBIDOS = (
    "Maria",
    "Conceição",
    "Oliveira",
    "Santos",
    "João",
    "Ana",
    "António",
    "Joana",
    "Pereira",
    "Carlos",
    "Mendes",
    "Sacavém",
    "Flores",
    "097865413",
    "12345678",
    "11223344556",
    "4111",
    "987654321",
    "ID-BIO",
    "FACE-ID",
    "12345-PT",
    "1978",
    "2018",
    "2019",
    "2022",
    "12/03",
    "09/27",
    "47",
    "52",
    "1,68",
    "72",
    "145/90",
    "O+",
    "62.500",
    "Premium",
)

VISIVEIS = (
    "Feminino",
    "hipertensão",
    "diabetes",
    "HIV",
    "hemograma",
    "glicemia",
    "ultrassonografia",
    "Divorciada",
    "Católica",
    "Professora",
    "Faculdade",
    "Ex-fumante",
    "álcool",
    "Metformina",
    "ansiosa",
    "trabalho",
    "mãe",
    "pai",
    "irmão",
)

EMAIL = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
TELEFONE = re.compile(
    r"(?:\+351[\s.-]?)?(?:9[1236]\d{7}|2\d{8})\b"
)
NIF = re.compile(r"\b\d{9}\b")
CARTAO = re.compile(r"\b\d{4}(?:[\s-]?\d{4}){3}\b")
ASTERISCOS = re.compile(r"\*{2,}")
SEXO = re.compile(r"(?im)^Sexo:\s*(.+)$")
NOME_PACIENTE = re.compile(r"(?m)^Nome:\s*(.+)$")
ALTURA = re.compile(r"(?im)^Altura:\s*(.+)$")
PESO = re.compile(r"(?im)^Peso:\s*(.+)$")


def contem(texto, palavra):
    if re.search(r"\w$", palavra):
        padrao = r"(?i)\b" + re.escape(palavra) + r"\b"
    else:
        padrao = r"(?i)(?<!\w)" + re.escape(palavra) + r"(?!\w)"
    return re.search(padrao, texto) is not None


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
        problemas.append("Número de 9 dígitos ainda visível: " + nif)

    for cartao in CARTAO.findall(texto):
        problemas.append("Cartão ainda visível: " + cartao)

    for asteriscos in ASTERISCOS.findall(texto):
        problemas.append(
            "Vários asteriscos juntos: " + asteriscos
            + ". Cada palavra mascarada é um só *."
        )

    for palavra in PROIBIDOS:
        if contem(texto, palavra):
            problemas.append("Identificador ainda visível: " + palavra)

    for palavra in VISIVEIS:
        if not contem(texto, palavra):
            problemas.append("Devia ficar visível: " + palavra)

    sexo = SEXO.search(texto)
    if sexo and sexo.group(1).strip() != "Feminino":
        problemas.append(
            "Sexo devia ficar visível: Sexo: " + sexo.group(1).strip()
        )

    nomes = NOME_PACIENTE.findall(texto)
    if nomes and nomes[0].strip() != "* * * *":
        problemas.append(
            "Nome do paciente deveria ser '* * * *': Nome: "
            + nomes[0].strip()
        )

    altura = ALTURA.search(texto)
    if altura and altura.group(1).strip() != "*m":
        problemas.append(
            "Altura deveria ser '*m': Altura: " + altura.group(1).strip()
        )

    peso = PESO.search(texto)
    if peso and peso.group(1).strip() != "*kg":
        problemas.append(
            "Peso deveria ser '*kg': Peso: " + peso.group(1).strip()
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
