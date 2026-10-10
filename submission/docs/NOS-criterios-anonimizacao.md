# NOS — Critérios de anonimização

Síntese de trabalho para a equipa CodingBros — 10/10/2026.

**Estado:** política proposta, ainda não validada pelos mentores. O enunciado pede ocultar dados sensíveis ou pessoais, mas não fornece uma lista completa. As decisões abaixo não são a referência oculta da avaliação.

## 1. Princípios

- Analisar o documento inteiro, incluindo narrativa, assinatura e dados de terceiros.
- Não considerar um identificador seguro só porque o nome foi removido: um NIF pode permitir ligar registos sem o nome ao lado.
- Distinguir três aspetos que podem coexistir: **identificação**, **informação sensível** e **risco por combinação**.
- Relacionar menções da mesma pessoa: nome completo, abreviado, primeiro nome e apelido, quando o contexto estabelecer essa ligação.
- Não confundir informação insuficiente para identificar sozinha com informação inofensiva.
- Não assumir que eliminar nomes garante anonimização do documento.
- Tratar os dados fictícios do desafio segundo a sua função; não os preservar apenas por serem fictícios ou falharem um checksum.

## 2. Ocultar — política proposta

| Dados | Critério |
|---|---|
| Nomes de pessoas | Ocultar nomes completos e menções parciais contextualmente ligadas, incluindo paciente, familiares e contactos. |
| NIF, Cartão de Cidadão e NISS | Ocultar os valores, mesmo sem nome próximo. Não aplicar a regra a qualquer número sem contexto. |
| Morada residencial completa | Ocultar o endereço associado à pessoa. |
| Telefones e emails pessoais | Ocultar os valores e verificar ocorrências repetidas. |
| Data de nascimento completa | Ocultar como identificador contextual forte. |
| Número de apólice | Ocultar por identificar uma relação contratual individual. |
| Cartão de pagamento, validade e CVV | Ocultar os valores associados ao cartão. |
| Referências individuais a registos biométricos | Ocultar códigos como IDs de impressão digital ou reconhecimento facial. O código não é a própria amostra biométrica. |
| Identificação e contactos nominativos do médico | Proposta inicial: ocultar nome, identificação profissional e contactos associados. Confirmar o tratamento dos profissionais com a NOS. |

## 3. Preservar — evidência explícita ou estrutural

O enunciado apresenta este início como exemplo de saída correta; preservá-lo neste contexto:

```text
Relatório de Admissão - Centro Médico Lisboa
Data: 15 de abril de 2025
Referência: ADM-2025-04-15-089
Informações do Paciente:
```

- Preservar rótulos e títulos como `Nome:`, `NIF:` e `Histórico Médico:`.
- Preservar o restante texto que a política não determine ocultar, sem reescrever frases.
- **Não generalizar a exceção do cabeçalho:** outras datas, instituições e referências podem estar associadas a pessoas e exigir ocultação.
- Uma instituição no título e a mesma instituição enquanto empregador de uma pessoa têm funções diferentes.

## 4. Avaliar por contexto e combinação

Rever conjuntamente idade, sexo, localidade, profissão, empregador, estado civil, composição familiar, datas e acontecimentos particulares.

Exemplo: **idade exata + profissão + faculdade concreta + filhos com determinadas idades** pode permitir reconhecimento, mesmo sem nome.

- As combinações podem atravessar linhas, secções e páginas.
- Não existe aqui um número fixo de atributos que prove identificação, nem uma percentagem de risco calculável só pela leitura.
- A equipa deve definir e documentar o que ocultar nestes casos; não deixar a decisão variar silenciosamente entre execuções.
- O formato do desafio exige asteriscos: não substituir uma idade por uma faixa etária nem uma morada por uma região sem autorização.

## 5. Dados sensíveis: decisão pendente da NOS

O documento contém informação clínica, genética, origem étnica, religião, hábitos, rendimento, características físicas e relações familiares. Estas categorias não são todas equivalentes e não devem ser automaticamente preservadas.

| Grupo | Exemplos presentes | Questão a resolver |
|---|---|---|
| Saúde e genética | Diagnósticos, HIV, BRCA1, dependência, sintomas, medicação, exames e sinais vitais | Ocultar também estes valores ou preservar a utilidade clínica após tratar os identificadores? |
| Religião e origem étnica | Convicção religiosa e descrição étnica | Confirmar os trechos a substituir; não presumir que são necessários ao contexto clínico. |
| Informação social e económica | Estado civil, filhos, profissão, empregador, rendimento e plano de seguro | Definir quais valores ocultar e como tratar combinações identificativas. |
| Características individuais | Altura, peso, idade e sexo | Avaliar contexto e combinações; não equiparar automaticamente a identificadores biométricos únicos. |
| Profissionais e relações | Médico, especialidade, contactos e parentesco | Distinguir dados pessoais, informação profissional genérica e possíveis ligações à paciente. |

**Preservar o significado não significa autorização para manter todos os dados clínicos.** Retirar identificadores e ocultar atributos sensíveis são objetivos distintos; o enunciado não resolve completamente a fronteira.

## 6. Regras de transformação e verificação

- Substituir cada palavra a anonimizar por um único `*`: `Ana Correia` → `* *`.
- Remover linhas vazias, conforme o enunciado; preservar a restante estrutura textual.
- Não acrescentar explicações, etiquetas como `[NOME]`, Markdown ou identificação da equipa em `submission.txt`.
- Confirmar a regra de contagem para telefones com espaços, datas, palavras hifenizadas e pontuação adjacente.
- Verificar nomes repetidos, identificadores restantes, ocultações excessivas e alterações indevidas ao texto.
- Regex identifica candidatos; não determina sozinha sensibilidade. Um verificador de formato não prova que todos os dados sensíveis foram removidos.
- Registar decisões e manter a política coerente. A avaliação interna não equivale à pontuação oficial.

## 7. Perguntas prioritárias aos mentores

1. Devemos ocultar apenas identificadores ou também informação clínica, genética, religião e origem étnica?
2. Como tratar idades, sexo, profissão, empregador, rendimento e composição familiar?
3. Devemos ocultar os dados do médico e manter apenas título/especialidade?
4. Como se definem palavras e limites de substituição em moradas, telefones e pontuação?

## Fontes e precedência

- Enunciado: [NOS — JunctionX Lisbon 2026](</Users/marco/Desktop/NOS - JunctionX Lisbon 2026.pdf>), especialmente página 2.
- Entrada: [document_to_anonymize.pdf](/Users/marco/Documents/GitHub/nos-gen-ai-hackathon/raw_data/document_to_anonymize.pdf).
- Textos auxiliares: [message (1).txt](</Users/marco/Downloads/message (1).txt>) e [message (2).txt](</Users/marco/Downloads/message (2).txt>); propostas de análise, não regras oficiais.
- Enquadramento: [RGPD, artigos 4.º e 9.º](https://eur-lex.europa.eu/eli/reg/2016/679/pt). As definições legais não especificam a saída esperada da hackathon.

Para a entrega, seguir as regras oficiais e os esclarecimentos dos mentores. Registar eventuais diferenças entre a política do exercício e uma avaliação de anonimização para utilização real.
