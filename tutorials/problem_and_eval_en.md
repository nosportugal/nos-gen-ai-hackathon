# Problem statement

**Objective:** Develop an LLM-based system capable of identifying and removing sensitive or personal data from documents.

## Guidelines

**1. Input:** 
   * Text document containing fictitious data. This document is the same for all teams. You can find it in `raw_data/document_to_anonymize.pdf`.

**2. Output:**

* **Anonymized document:** 
   * Text document with the sensitive data replaced with a single `*` for each anonymized word (e.g.: Ana Correia -> * *)
   * This document should maintain the original document's formatting, but with no empty lines. Example:
   ```text
   Relatório de Admissão - Centro Médico Lisboa
   Data: 15 de abril de 2025
   Referência: ADM-2025-04-15-089
   Informações do Paciente:
   ```

**3. Technical Requirements**

* **Prompt Engineering:** Use prompt engineering techniques to instruct the LLM to detect patterns and contextualize sensitive data.
* **Meaning Preservation:** Ensure the anonymization logic preserves the document's original meaning.
* **Manual Validation (Optional):** Include the possibility of manual validation for false positives/negatives.


# Project Evaluation

## 1. Evaluation Criteria

The evaluation of the project will be based on the following criteria:

**1.1 Technical Implementation (40%)**

* **Precision (10%):** Detection Hit Rate.
* **Prompt (10%):** Prompt and response quality.
* **Anonymization Quality (5%):** Preservation of context after removing sensitive data.
* **Explicability (5%):** The solution's clarity and technical rigor.
* **Efficiency (5%):** Optimized usage of prompts and engineering techniques.
* **GitHub (5%):** Code quality (structure, branch usage, merges and commits in Git)


**1.2 Collaboration (30%)**

* Shared commit history and integration between team members.


**1.3 Documentation (10%)**

* Clarity, organization and technical detail of the project (README, usage and setup instructions).


**1.4 Pitch Creativity (20%)**

* Originality, impact and communication. (Maximum 2 minutes per team).


## 2. General Rules

* The use of open-source frameworks and packages is allowed, granted they are referenced.
* All projects must include clear documentation (README, usage and setup instructions).
* The commit history will be analyzed to evaluate the usage of good collaborative development practices.
* The final pitch will be at most 2 minutes per team.
* Failure to comply with the rules may mean immediate disqualification.


## 3. Open-Source Intellectual Property

* **Open-Source License:** The source code of the project must be made available with an open-source license.
* **Public Repository:** The source code must be made available in a public repository (e.g., GitHub).
* **Repurpose:** The parties may reuse the work for other non-commercial purposes.


## 4. Prizes

The winning team receives tickets for NOS Alive 2027, one for each team member.
