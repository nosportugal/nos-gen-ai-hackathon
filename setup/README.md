# [Nos Gen Ai Hackathon]

[![Project Status](https://img.shields.io/badge/status-in%20development-green)](https://www.repostatus.org/#wip)

[![GitHub Contributors](https://img.shields.io/github/contributors/JoseMariano247)](https://github.com/JoseMariano247)
[![GitHub Contributors](https://img.shields.io/github/contributors/figipef)](https://github.com/figipef)
[![GitHub Contributors](https://img.shields.io/github/contributors/0tilarr)](https://github.com/0tilarr)
[![GitHub Contributors](https://img.shields.io/github/contributors/Formiga03)](https://github.com/Formiga03)

[![License](https://img.shields.io/badge/license-[Your%20License]-blue.svg)](LICENSE) A brief and engaging description of your project. What problem does it solve? What are its key features? Keep it concise and interesting.

## Table of Contents

- [About](#about)
- [How We Did It](#how-we-did-it)
- [Production Steps](#production-steps)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Collaborators](#collaborators)
- [Contact](#contact)

## About

Given a .pdf file with sensative information we extract the text from the whole file and throught a gemini prompt redact it basing ourselves in the EU regulations on the "Regulation (EU) 2016/679 (General Data Protection Regulation)".

## How We Did It

This section should detail the development process and the technologies used.

- **Technology Stack:** List the main programming languages, frameworks, libraries, and tools you utilized.
  ```
  - Language: Python;
  - Libraries: PyMuPDF, fitz;
  - Tools: Google Colab, GitHub.
  ```
## Production Steps

In order to develop our solution for the problem, we split the task in 4 parts:

1.  **Environment setup on GitHub and Google Colab;**
2.  **PDF Reader Function;** 
3.  **Prompt Developement;** 
4.  **Prompt Application on the output of the Reader Function;**
5.  **Code Testing.**

## Getting Started



### Prerequisites

List any software or tools that need to be installed before they can work on the project. Be specific with versions if necessary.

- [Node.js](https://nodejs.org/) (version >= 16.0.0)
- [Python](https://www.python.org/) (version >= 3.9)
- [Docker](https://www.docker.com/)
- [Specific database system]

### Installation

Provide clear, step-by-step instructions on how to get the project running on a local machine.

1.  Clone the repository:
    ```bash
    git clone git@github.com:figipef/nos-gen-ai-hackathon.git
    ```
2.  Navigate to the project directory:
    ```bash
    cd nos-gen-ai-hackathon
    ```
3.  Install dependencies (example for Python):
    ```bash
    pip install PyMuPDF
    pip install fitz
    ```

## Usage

Firstly add the pdf file to the raw_dat directory and then on the main directory run the line "python3 setup/main.py" or "python3 submission/main.py" 


## Collaborators

List the main collaborators on the project. You can include their GitHub usernames and optionally a brief description of their contributions.

- [GitHub figipef](https://github.com/figipef) - PDF file reader fucntion
- [GitHub 0tilarr](https://github.com/0tilarr) - Prompt development
- [GitHub JoseMariano247](https://github.com/JoseMariano247) - Prompt application code
- [GitHub Formiga03](https://github.com/Formiga03) - ReadMe file and slides

