# NOS Challenge — JunctionX Lisbon 2026

Welcome to the NOS challenge repository for **JunctionX Lisbon 2026** (10–11 October 2026, IST — Campus Taguspark, Porto Salvo, Lisbon). In this repository you will find the problem statement, code snippets and examples to help you get started, plus the submission folder that is scored automatically when you open a pull request.

**The challenge:**  build an LLM-based system that finds and masks sensitive data in a document, preserves its meaning and formatting.

**Quick facts**

- Submission = a pull request to `main` (see [section 4](#4-submission-guidelines)).
- Questions: ask the NOS mentors on site, or on the organization's Discord.

## 0. Problem Statement and Evaluation Criteria

For a complete description of the problem statement and the detailed evaluation criteria, refer to this [document](tutorials/problem_and_eval_en.md).*

The document to be anonymized is located at [`raw_data/document_to_anonymize.pdf`](raw_data/document_to_anonymize.pdf).

## 1. Prerequisites
Before the event, please ensure that you meet the following prerequisites. Having the needed accounts and accesses will help streamline your development process and facilitate the use of necessary tools and APIs.

### 1.1. GitHub Account

Make sure you have an active GitHub account at [Create a GitHub Account](https://github.com/signup)

### 1.2. Google Account

You'll need an active Google account to access Google AI tools at [Create a Google Account](https://accounts.google.com/signup)

### 1.3. Set Up Your Google API Key

To generate your API key:

a. Go to [Google AI Studio](https://aistudio.google.com/) and log in with your Google account.  
b. Click on the **“Get API Key”** button.  
c. Select **“Create API key”**.  
d. A window will open where you’ll create an API key under a new project.  
e. **Important:** Save the generated API key in a safe place — you'll need it later!

## 2. Setup
In this section, we'll walk you through the essential setup steps needed to get started with your project. Follow these instructions carefully!

### 2.0. Get the repository

1. **Fork** this repository to your GitHub account (one fork per team; one team member owns it and adds the others as collaborators).
2. Clone your fork and create a working branch (e.g. `team-<name>`). Never work directly on `main`.
3. Work inside `submission/` as described in the [Submission Process Guide](submission/README.md).

### 2.1. Git tutorial

If you're new to Git, it’s important to understand how to manage your code effectively. To help you get started, we have provided a Git tutorial at [Git Tutorial](tutorials/git_tutorial.md). This tutorial will guide you through the fundamental concepts and commands you'll need to commit your changes and collaborate with your team.

## 3. Utils

This section contains helpful resources and tools to support your work.

### 3.1. Getting Started with Gemini API

If you're looking for **detailed steps**, including how to obtain an API key and example usage, please refer to the full tutorial at [Gemini API Tutorial](tutorials/gemini_tutorial.md)

### 3.2. Document Conversion Methods

Converting PDF documents to text can be essential for leveraging existing content in your project. There are methods and tools available for this conversion, which you can explore in detail in the [PDF to Text Guide](tutorials/pdf__to__txt.ipynb).


## 4. Submission Guidelines

Opening a pull request against `main` triggers the automatic evaluation workflows (see `.github/workflows/`), so you get a score as soon as you submit. The final submission must be in before the end of the challenge.

In this section, we will outline the expectations for project submission. Understanding these guidelines is crucial to ensure your work is evaluated correctly. There are specific methods and criteria for submission, which you should follow closely to enhance your chances of success. Make sure to read through the following points carefully.
For more detailed information on the submission process and what is expected, please refer to the [Submission Process Guide](submission/README.md).
