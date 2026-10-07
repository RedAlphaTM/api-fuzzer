# API Fuzzer

A Python-based HTTP endpoint fuzzer for discovering and analyzing application responses through wordlist-based GET and POST requests.

## Why I Built This

I built this project as a hands-on cybersecurity learning project to better understand HTTP behavior, endpoint discovery, concurrency, response analysis, and the challenges involved in distinguishing genuinely interesting responses from normal application behavior.
The project started as a basic wordlist-based endpoint fuzzer and was gradually expanded with GET and POST support, concurrent requests, response baselining, and response-aware classification.

## Features

- Wordlist-based HTTP endpoint fuzzing
- GET and POST request support
- JSON request-body parsing and submission
- Concurrent request processing with `ThreadPoolExecutor`
- URL context extraction
- Context-specific response baselining
- Response grouping based on status code, Content-Type, response size, and body similarity
- Possible soft-404 detection using multiple response signals
- Optional HTTP redirect following
- Configurable request timeout
- Response reporting with status code, response size, response time, and endpoint
- Graceful handling of connection and request failures
- Debug output for inspecting baseline collection and response analysis

## Installation

### Requirements

- Python 3.x
- `requests`

### Setup

Clone the repository and enter the project directory:

```bash
git clone <your-repository-url>
cd api-fuzzer
```
Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```
Install the required dependency:

```bash
python -m pip install -r requirements.txt
```

## Usage

### Basic GET Fuzzing

The fuzzer reads endpoint candidates from standard input. A wordlist can be piped into the program:

```bash
cat words.txt | python3 apifuzzer2.py http://127.0.0.1:5000
```

### POST Requests

The fuzzer can send JSON request data with POST requests using the `--method` and `--data` options.

Example:

```bash
cat words.txt | python3 apifuzzer2.py http://127.0.0.1:5000 \
    --method POST \
    --data '{"username":"admin","password":"password123"}'
```

The example uses the local Flask application included in this repository.

### Concurrent Requests

The number of worker threads can be configured with the `--threads` option.

Example:

```bash
cat words.txt | python3 apifuzzer2.py http://127.0.0.1:5000 --threads 20
```

This allows multiple HTTP requests to be processed concurrently, which can improve throughput when the program is waiting on network I/O.

### Request Timeout

The request timeout can be configured with the `--timeout` option.

Example:

```bash
cat words.txt | python3 apifuzzer2.py http://127.0.0.1:5000 --timeout 10
```

The timeout controls how long the fuzzer waits for an HTTP request before treating it as a request failure.

### Debug Mode

Debug output can be enabled with the `--debug` option.

Example:

```bash
cat words.txt | python3 apifuzzer2.py http://127.0.0.1:5000 --debug
```

When a context has been identified as a missing-resource baseline, debug mode provides additional information about response similarity and the signals used during possible soft-404 analysis.

If a context only has a generic baseline, the additional soft-404 analysis is not performed, so debug mode does not produce additional classification details for that context.

### Redirect Handling

Redirects are not followed by default. The `--follow-redirects` option enables redirect following when needed.

Example:

```bash
cat words.txt | python3 apifuzzer2.py http://127.0.0.1:5000 --follow-redirects
```

Keeping redirect following optional allows the original `301` or `302` response to remain visible during normal fuzzing.

## How It Works

The fuzzer follows a multi-stage process:

1. Reads endpoint candidates from standard input.
2. Extracts URL contexts from the supplied wordlist.
3. Sends randomized probe requests to each context to establish a response baseline.
4. Groups probe responses using status code, Content-Type, response size, and body similarity.
5. Selects a qualifying baseline when the responses are sufficiently consistent.
6. Classifies a baseline as a missing-resource baseline when its representative response uses a `404` or `410` status code.
7. Fuzzes the supplied endpoints concurrently.
8. Compares responses against the appropriate context-specific baseline.
9. Performs additional soft-404 analysis when a missing-resource baseline is available.
10. Reports the resulting response classification.

## Response Baselines

Before fuzzing endpoints, the fuzzer sends randomized probe requests to each URL context to establish a baseline for how the application normally responds to nonexistent or unknown paths.

Responses are grouped using their:

- HTTP status code
- `Content-Type`
- Response size
- Body similarity

A sufficiently consistent group is selected as the context's baseline. Baselines returning `404` or `410` are classified as `missing-resource` baselines and can be used for additional soft-404 analysis.

## Soft-404 Detection

Some applications return `200 OK` for nonexistent endpoints instead of a normal `404`. These responses can create false positives during endpoint fuzzing.

The fuzzer compares `200` responses against the appropriate missing-resource baseline using response-body similarity and additional signals such as known not-found phrases, response size, and HTML content type.

When enough signals indicate that a `200` response is likely a disguised not-found page, it is reported as:

```text
POSSIBLE SOFT-404
```

This classification is intentionally labeled as **possible** rather than definitive to avoid treating heuristic detection as proof.

## Testing & Validation

The fuzzer was tested in controlled local environments to verify request handling, response classification, error handling, and baseline analysis.

### Flask Test Application

A custom Flask application was used to test:

- `200`, `400`, `401`, and `404` responses
- GET and POST requests
- Method handling and `405` responses
- Soft-404 detection
- Connection failures

The tests confirmed that the fuzzer could distinguish normal responses from several intentionally crafted soft-404 cases.

### OWASP Juice Shop

The fuzzer was also tested against a local OWASP Juice Shop instance to observe its behavior against a more realistic web application.

Testing included:

- `200` responses from valid and SPA fallback routes
- `500` responses from invalid API paths
- `301` redirects
- Valid API responses

These tests helped evaluate how the fuzzer behaves when an application uses different response patterns across different parts of the application.

## Limitations & Scope

This project is intentionally focused on HTTP endpoint discovery and response analysis rather than full vulnerability scanning.

It does **not** currently perform:

- SQL injection or XSS testing
- Authentication or credential brute forcing
- Parameter fuzzing
- OpenAPI/Swagger parsing
- Application crawling or JavaScript analysis
- Exploit generation

The fuzzer is intended for authorized security testing and controlled lab environments.

## Project Structure

```text
api-fuzzer/
├── apifuzzer2.py
├── testapi2.py
├── words.txt
├── juice_words.txt
├── requirements.txt
└── .gitignore
```
