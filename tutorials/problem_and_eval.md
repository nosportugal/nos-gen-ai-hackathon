# Enunciado

*Note: This document is intentionally written in Portuguese as it is targeted at a Portuguese-speaking audience.*

**Objetivo:** Desenvolver um sistema baseado em Large Language Models (LLMs) que identifique e remova automaticamente dados sensíveis ou pessoais de documentos, gerando um relatório explicativo.

## Diretrizes

**1. Entrada:** 
   * Documento de texto contendo informações fictícias. Este documento será igual para todas as equipas. Encontra-se presente em `raw_data/document_to_anonymize.pdf`.

**2. Saída:**

* **Documento anonimizado:** 
   * Documento com dados sensíveis substituídos por `*` por cada palavra a ser anonimizada (ex: Ana Correira -> * *)
   * Deve manter a formatação original do documento, mas sem linhas vazias. Como exemplo:
   ````text
    Relatório de Admissão - Centro Médico Lisboa
    Data: 15 de abril de 2025
    Referência: ADM-2025-04-15-089
    Informações do Paciente:
    ````

**3. Requisitos Técnicos**

* **Prompt Engineering:** Utilizar técnicas de prompt engineering para instruir o LLM a detectar padrões e contextualizar dados sensíveis.
* **Preservação do Significado:** Garantir que a lógica de anonimização preserve o significado original do documento.
* **Validação Manual (Opcional):** Incluir a possibilidade de validação manual para falsos positivos/negativos.


# Avaliação do Projeto

## 1. Critérios de Avaliação

A avaliação do projeto será baseada nos seguintes critérios:

**1.1 Implementação Técnica (40%)**

* **Precisão (10%):** Taxa de acerto na deteção.
* **Prompt (10%):** Qualidade da prompt e da resposta.
* **Qualidade da Anonimização (5%):** Preservação do contexto após remoção de informações sensíveis.
* **Explicabilidade (5%):** Clareza e rigor técnico da solução.
* **Eficiência (5%):** Uso otimizado de prompts e técnicas de engenharia.
* **GitHub (5%):** Qualidade do código (estrutura, uso de branches, merges e commits no Git).


**1.2 Colaboração (30%)**

* Histórico de commits compartilhados e integração entre membros da equipe.


**1.3 Documentação (10%)**

* Clareza, organização e detalhe técnico do projeto (README, instruções de uso e setup).


**1.4 Criatividade do Pitch (20%)**

* Originalidade, impacto e comunicação.  (Apresentação máxima de 2 minutos por equipa).


## 2. Regras Gerais

* O uso de frameworks e bibliotecas open-source é permitido, desde que referenciados.
* Todos os projetos devem incluir documentação clara (README, instruções de uso e setup).
* O histórico de commits e branches será analisado para avaliar as boas práticas de desenvolvimento colaborativo.
* O pitch final terá duração máxima de 2 minutos por equipa.
* O não cumprimento das regras pode levar à desclassificação imediata.


## 3. Propriedade Intelectual Open-Source

* **Licença Open-Source:** O código do projeto deverá ser disponibilizado sob uma licença open-source.
* **Repositório Público:** O código-fonte deve ser disponibilizado num repositório público (e.g., GitHub).
* **Reutilização:** As partes podem reutilizar o trabalho para outros fins não comerciais.


## 4. Premiação

A equipa vencedora recebe bilhetes para o NOS Alive 2027, um para cada membro.
