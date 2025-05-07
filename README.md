# NOS Gen-AI Hackathon

Welcome to the official attempt of group #8 at the NOS Gen-AI Hackathon. In this repository you will find a system based in a Google Large Language Model (LLM), Gemma that removes sensible and personal data of documents in the format of a pdf. The output is, also, a pdf file with an explainable report.

## 1. PDF to Text
 - Converting a PDF to plain text provides the LLM with a clean, linear sequence of words that it is designed to process. 
 - Once the text is extracted, the LLM can leverage its strengths in natural language understanding, including identifying entities, understanding relationships between words, and answering questions.
 - Most existing tools, libraries, and techniques for working with LLMs are optimized for text data.

## 2. Gemma LLM Analysis
 - Our core functionality relies on the Gemma LLM to analyze the extracted text and the user provided prompt.
 - It generates the most relevant and accurate response.
 - The system detects and removes personal and sensitive data sush as names, emails, phone numbers and any other identifiable data.

## 3. Text to PDF
 - Converts the text output back to PDF format.


## RUN THE main.ipynb FILE FROM THE MAIN BRANCH.

![EL GATO](tutorials/images/cat.png)
