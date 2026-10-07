import json
import requests
import secrets
import difflib
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor

# Default headers sent with every request
headers = {
    "User-Agent": "ApiFuzzer/1.0"
}

# Status codes to process and display
interested_codes = {200, 301, 302, 400, 401, 403, 404, 405, 500}

# Create the argument parser
parser = argparse.ArgumentParser(
    description="Simple API endpoint fuzzer"
)

# Required positional argument
parser.add_argument(
    "base_url",
    help="Base URL of target API"
)

parser.add_argument(
    "--method",
    choices=["GET", "POST"],
    default="GET",
    help="HTTP method to use"
)

parser.add_argument(
    "--threads",
    type=int,
    default=10,
    help="Number of worker threads"
)

parser.add_argument(
    "--data",
    help="JSON request data"
)

parser.add_argument(
    "--timeout",
    type=int,
    default=5,
    help="Request timeout"
)

parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug output"
)

parser.add_argument(
    "--follow-redirects",
    action="store_true",
    help="Follow HTTP redirects"
)

args = parser.parse_args()

if args.threads < 1:
    print("Invalid thread count: --threads must be at least 1")
    sys.exit(1)

if args.timeout < 1:
    print("Invalid timeout: --timeout must be greater than 0")
    sys.exit(1)

# Parse JSON request data if supplied
try:
    if args.data:
        request_data = json.loads(args.data)
    else:
        request_data = None
except json.JSONDecodeError:
    print("Invalid JSON supplied with --data")
    sys.exit(1)

# Remove any trailing slash
base_url = args.base_url.rstrip("/")

# Create one Session for the entire program
session = requests.Session()

# Common arguments for HTTP requests
request_args = {
    "headers": headers,
    "timeout": args.timeout,
    "allow_redirects": args.follow_redirects
}

# Add JSON data only if --data was supplied
if request_data is not None:
    request_args["json"] = request_data

# Phrases indicating a likely missing endpoint
strong_phrases = [
    "endpoint not found",
    "requested endpoint does not exist",
    "requested path does not exist",
    "resource not found",
    "page you requested could not be found",
    "route not found",
    "page not found"
]
# Phrases providing weaker error evidence
supporting_phrases = [
    "not found",
    "could not be found"
]

def print_response(word, res):
    print(
        f"{res.status_code:3} | "
        f"{len(res.content):5} bytes | "
        f"{res.elapsed.total_seconds():.3f}s | "
        f"{word}",
        flush=True
    )



def fuzz_endpoint(word):
    word = word.strip().rstrip("/")

    if not word:
        return

    parts = word.split("/")
    if len(parts) == 1:
        context = "/"
    else:
        context = "/".join(parts[:-1]) + "/"

    baseline_info = baselines.get(context)
    if baseline_info is None:
        baseline = None
        baseline_type = None
    else:
        baseline = baseline_info["response"]
        baseline_type = baseline_info["type"]

    url = f"{base_url}/{word}"

    try:
        res = session.request(
            args.method,
            url,
            **request_args
        )

        if res.status_code not in interested_codes:
            return

        if baseline is None:
            print_response(word, res)
            return
        if baseline_type != "missing-resource":
            print_response(word, res)
            return

        similarity = difflib.SequenceMatcher(
                None,
                baseline.text,
                res.text
            ).ratio()


        if args.debug:
            print(
                f"[DEBUG] {word} | "
                f"sim = {similarity:.2%}",
                flush=True
        )

        # Convert response body to lowercase for phrase matching
        body_lower = res.text.lower()

        # Evidence used to classify the response
        strong_signals = []
        supporting_signals = []

        # Check for strong and supporting error phrases
        strong_phrase_found = False
        supporting_phrase_found = False

        for phrase in strong_phrases:
            if phrase in body_lower:
                strong_phrase_found = True
                break

        for phrase in supporting_phrases:
            if phrase in body_lower:
                supporting_phrase_found = True
                break

        # Classify similarity evidence
        if similarity >= 0.90:
            strong_signals.append("similarity")

        # Classify phrase evidence
        if strong_phrase_found:
            strong_signals.append("phrase")
        elif supporting_phrase_found:
            supporting_signals.append("phrase")

        length_difference = abs(
            len(baseline.content) - len(res.content)
        )
        if length_difference <= 5:
            supporting_signals.append("length")
        # Get the response Content-Type
        content_type = res.headers.get(
            "Content-Type",
            ""
        )

        # Treat HTML response as supporting evidence
        if content_type.startswith("text/html"):
            supporting_signals.append("content-type")

        # Flag as a possible soft-404 only when:
        # - Response is 200
        # - Strong similarity has at least one supporting signal
        # - OR a strong missing-resource phrase is detected
        if (
            res.status_code == 200
            and (
                (

                    "similarity" in strong_signals
                    and len(supporting_signals) >= 1
                )
                or (
                    "phrase" in strong_signals
                )
            )
        ):

            signal_reasons = (
                strong_signals +
                supporting_signals
            )

            print(
                f"POSSIBLE SOFT-404 | {word} | "
                f"strong={len(strong_signals)} | "
                f"supporting={len(supporting_signals)} | "
                f"similarity{similarity:.2%} | "
                f"reasons={','.join(signal_reasons)}",
                flush=True
            )

            return

        print_response(word, res)

    except requests.RequestException as e:
        print(
            f"ERROR | {word} | {type(e).__name__}: {e}",
            flush=True
        )


# ---------------------------------------------------------
# READ WORDLIST
# ---------------------------------------------------------

words = []
contexts = set()

for word in sys.stdin:
    word = word.strip().rstrip("/")

    if not word:
        continue

    words.append(word)

    parts = word.split("/")

    if len(parts) == 1:
        context = "/"
    else:
        context = "/".join(parts[:-1]) + "/"

    contexts.add(context)

print("\n[+] Contexts found:")

for context in contexts:
    print(f" - {context}")

# ---------------------------------------------------------
# BASELINE COLLECTION
# ---------------------------------------------------------

probe_count = 10

baselines = {}

for context in contexts:
    print(f"\n[+] Collecting probes for context: {context}")

    responses = []

    for _ in range(probe_count):

        random_hex = secrets.token_hex(8)

        if context == "/":
            probe_url = f"{base_url}/{random_hex}"
        else:
            probe_url = f"{base_url}/{context}{random_hex}"

        try:
            probe_response = session.request(
                args.method,
                probe_url,
                **request_args
            )

        except requests.RequestException as e:
            print(
                "[-] Critical Error connecting while collecting "
                "baseline responses."
            )
            print(f"[-] Details: {e}")
            sys.exit(1)

        responses.append(probe_response)

    print(f"[+] Collected {len(responses)} probe responses")
    for i, response in enumerate(responses, start=1):
        print(
            f" Probe {i} -> "
            f"{response.status_code} | "
            f"{len(response.content)} bytes | "
            f"{response.headers.get('Content-Type', '')}"
        )

    # GROUP RESPONSES FOR THIS CONTEXT
    groups = {}
    next_group_id = 1

    for response in responses:
        matched_group = None

        for group_id, group in groups.items():
            representative = group["representative"]

            if response.status_code != representative.status_code:
                continue
        # Compare Content-Type
            response_type= response.headers.get("Content-Type", "")
            representative_type = representative.headers.get("Content-Type", "")

            if response_type != representative_type:
                continue
        # Compare response size
            response_size = len(response.content)
            representative_size = len(representative.content)

            if abs(response_size - representative_size) > 5:
                continue
        # Compare response bodies
            similarity = difflib.SequenceMatcher(
                None,
                response.text,
                representative.text,
            ).ratio()

            if similarity >= 0.80:
                matched_group = group_id
                break
    # Add response to an existing group
        if matched_group is not None:
            groups[matched_group]["responses"].append(response)
        else:
            groups[next_group_id] = {
                "representative": response,
                "responses": [response]
            }
            next_group_id += 1

    print("\n[+] Response groups")

    frequency_threshold = 0.70

    for group_id, group in groups.items():
        representative = group["representative"]
        frequency = len(group["responses"]) / len(responses)

        print(
            f"Group {group_id} -> "
            f"{len(group['responses'])} responses | "
            f"{frequency:.0%} | "
            f"{representative.status_code} | "
            f"{len(representative.content)} bytes | "
            f"{representative.headers.get('Content-type', '')}"
        )

        if frequency >= frequency_threshold:
            print(f" [+] Meets {frequency_threshold:.0%} baseline frequency threshold")
            status_evidence = representative.status_code in {404, 410}

            if status_evidence:
                print(" [+] Status code supports missing-resource behaviour")

            content_type = representative.headers.get("Content-Type", "").lower()
            html_evidence = "text/html" in content_type
            json_evidence = "application/json" in content_type

            if html_evidence:
                print(" [+] Content-Type is HTML")
            if json_evidence:
                print(" [+] Content-Type is JSON")

            size_consistent = all(
                abs(len(response.content) - len(representative.content)) <= 5
                 for response in group["responses"]
             )
            if size_consistent:
                print(" [+] Response size is consistent")

            body_consistent = all(
                difflib.SequenceMatcher(
                None,
                response.text,
                representative.text
            ).ratio() >= 0.90
            for response in group["responses"]
            )
            if body_consistent:
                print(" [+] Response bodies are highly consistent")

            if frequency >= frequency_threshold and size_consistent and body_consistent:
                baseline_type = "generic"
                if representative.status_code in {404, 410}:
                    baseline_type = "missing-resource"
                baselines[context] = {
                    "response": representative,
                    "type": baseline_type
                }



# ---------------------------------------------------------
# THREADING
# ---------------------------------------------------------

with ThreadPoolExecutor(
    max_workers=args.threads
) as executor:

    executor.map(
        fuzz_endpoint,
        words
    )
