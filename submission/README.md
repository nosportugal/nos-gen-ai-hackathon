# Implementação

Esta pasta contém a entrega do desafio de anonimização do NOS Gen-AI Hackathon. O programa lê o PDF definido pelo repositório, envia o texto e as instruções de anonimização à API Gemini e guarda a resposta em `submission.txt`.

O objetivo é substituir dados que possam identificar uma pessoa por asteriscos, preservando o conteúdo clínico e a estrutura do documento. A abordagem segue o enunciado e os critérios de avaliação ligados no [README principal](../README.md). O pitch apresenta o prompt detalhado como núcleo da solução e descreve a validação com asserções como forma de medir a qualidade.

## Como funciona

1. `anonymize.py` lê `prompt.txt` e pede o texto do documento a `code.py`.
2. O texto extraído é acrescentado às instruções, precedido por `Documento:`, porque o prompt atual não contém o marcador `{{DOCUMENTO}}`.
3. O programa envia a instrução completa ao modelo `gemini-3.8-flash`, usando a API Google Generative Language.
4. A resposta textual é gravada em `submission.txt` e passada a `checks.py`, que apresenta eventuais problemas encontrados.

## Ficheiros desta entrega

| Ficheiro | Função |
| --- | --- |
| `anonymize.py` | Orquestra a execução. Carrega a chave de API do `.env` na raiz, lê o prompt, obtém o texto do PDF, chama o Gemini e grava a resposta. Tem um limite de 300 segundos para a chamada e apresenta mensagens para erros de comunicação ou respostas sem texto. |
| `code.py` | Abre `raw_data/document_to_anonymize.pdf` com PyMuPDF e junta o texto de todas as páginas, pela ordem original. Extrai a camada de texto do PDF; não executa OCR. |
| `checks.py` | Verifica o resultado com regras específicas para este documento: presença de linhas obrigatórias, ausência de linhas vazias, padrões de email, telefone, NIF/números de 9 dígitos e cartões, termos que devem ser ocultados ou preservados e formatos esperados para nome, altura e peso. Pode também ser executado isoladamente para validar o ficheiro já gravado. |
| `prompt.txt` | Contém as instruções enviadas ao modelo. Define o que anonimizar e preservar, pede que se mantenham redação, ordem e pontuação e especifica a substituição de cada palavra ou número sensível por um `*`. |
| `submission.txt` | Contém apenas a resposta produzida pelo modelo, conforme as regras de entrega do desafio; não inclui explicações sobre a solução. |

## Prompt e decisões de anonimização

O prompt decide pelo contexto, não apenas pelo formato do dado. Pede a ocultação de identificadores como nomes, datas de nascimento, contactos, documentos, morada, biometria e valores financeiros. Ao mesmo tempo, preserva informação clínica e social como diagnósticos, sintomas, exames, tratamentos, estado civil, religião, profissão e relações familiares.

O prompt também fixa exceções próprias do documento, como o título, a instituição, a data do relatório, a referência e a especialidade. Essas instruções ajudam a manter o contexto e as linhas estruturais necessárias para a avaliação.

## Validação

`checks.py` combina expressões regulares com listas explícitas de valores proibidos e de conteúdo que deve continuar visível. Assim, serve como verificação automática e rápida da resposta para o documento do desafio. O verificador não edita nem corrige o texto: durante `anonymize.py`, apenas imprime os problemas que encontrar. Executado diretamente, termina com código de erro se houver problemas.

As regras são específicas ao documento e aos casos previstos em `checks.py`; não constituem um detetor geral de dados pessoais. A qualidade final também depende da resposta do modelo e da revisão das regras e do resultado.

O pitch descreve ainda um banco de asserções construído com Promptfoo e a comparação entre seis técnicas de prompt engineering. Segundo essa apresentação, as instruções detalhadas tiveram melhor resultado do que o zero-shot, enquanto as técnicas mais avançadas não aumentaram a precisão e demoravam cerca de três vezes mais. Essa comparação fundamenta a escolha de um prompt direto; não faz parte do fluxo de execução de `anonymize.py`.

## Configuração e execução

É necessário Python e uma chave da API Gemini. Na raiz do repositório, cria-se o ficheiro `.env` com uma das variáveis reconhecidas pelo programa (`GEMINI_API_KEY`, `GOOGLE_API_KEY` ou `API_KEY`). O `.gitignore` já exclui ficheiros `.env`; a chave deve permanecer local.

Instala as dependências e executa a partir da pasta `submission`:

~~~powershell
cd submission
py -m pip install requests python-dotenv pymupdf
py anonymize.py
~~~

A execução a partir de `submission` é necessária porque `code.py` usa o caminho relativo `../raw_data/document_to_anonymize.pdf`. Para validar separadamente o resultado gravado, ainda na pasta `submission`, executa:

~~~powershell
py checks.py
~~~

O ficheiro de entrada esperado é `raw_data/document_to_anonymize.pdf`, na raiz do repositório. O modelo e o endpoint da API estão definidos em `anonymize.py`.