# fiaca

Terminal client for working with AI models through their APIs, starting with
free models from [OpenRouter](https://openrouter.ai). The project is
intentionally small: first we provide a contextual chat session with
interchangeable providers, then we add coding tools (reading files, applying
patches, and running commands) behind explicit permissions.

## What it does today

- Interactive session with conversation history while the process is running.
- Local SQLite persistence for sessions and messages.
- Read-only workspace inspection with Git and validation command detection.
- Interactive terminal dashboard for inspecting the current project.
- Paste-friendly multiline chat input with an explicit submit shortcut.
- Rich Markdown rendering for assistant responses and Markdown documents.
- Read-only tasks that send selected workspace context to the provider.
- Providers compatible with the OpenAI chat API (OpenRouter, Groq, Together,
  Cerebras, and local servers such as Ollama).
- Credentials loaded from environment variables or a local `.env` file.
- Free OpenRouter model by default.
- Visible configuration errors and request failures in the terminal.

It is not a graphical application or a router that promises identical free
plan limits across providers. Each provider keeps its own limits, available
models, and terms of use.

## Installation

```bash
uv sync
source .venv/bin/activate
```

## Local API keys with `.env`

The recommended setup for local development is to copy `.env.example` to
`.env` and add the keys you use:

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
OPENROUTER_API_KEY=your-api-key
```

`.env` is excluded by Git, and Fiaca loads it automatically from the project
directory. You can also use `export OPENROUTER_API_KEY=...` if you prefer not
to store the key in a file. Explicitly exported environment variables take
precedence over values from `.env`.

## First use with OpenRouter

1. Create the configuration:

   ```bash
   fiaca config
   ```

   This writes `~/.fiaca.yml` without copying any API key to that file.

2. Start a session:

   ```bash
   fiaca chat
   ```

   Interactive chat accepts multiline input. Press `Enter` to send the message
   and `Alt-Enter` to add a new line. `Ctrl-S` remains available as a fallback
   on terminals that pass it through, but some terminals reserve it for flow
   control. `Ctrl-C` cancels the current draft, and `/exit` or `Ctrl-D` leaves
   the session. This makes it possible to paste prompts, code, errors, and
   structured requests without fighting the terminal.

   After submission, Fiaca displays `Sending...` while waiting for the
   provider. Network timeouts and connection failures are reported as
   recoverable messages so the session remains usable.

   Or send a one-off prompt:

   ```bash
   fiaca chat "Explain this Python error"
   ```

## Add another compatible provider

The configuration uses an endpoint compatible with `/chat/completions`:

```bash
fiaca config \
  --provider groq \
  --base-url https://api.groq.com/openai/v1 \
  --api-key-env GROQ_API_KEY \
  --model llama-3.1-8b-instant
```

Then:

```bash
export GROQ_API_KEY="your-api-key"
fiaca chat --provider groq
```

For a local server without an API key:

```bash
fiaca config \
  --provider ollama \
  --base-url http://localhost:11434/v1 \
  --model qwen2.5-coder:7b \
  --api-key-env ""
```

List configured providers:

```bash
fiaca providers
```

## Inspect a workspace

Launch the interactive dashboard:

```bash
fiaca
# or
fiaca ui
```

The dashboard shows the workspace, Git branch, modified file count,
configured providers, and recent sessions. Its actions currently cover
read-only inspection, file reading, search, and session browsing. It does not
apply changes or execute commands.

Run these commands from a project directory:

```bash
fiaca inspect
fiaca doctor
```

`fiaca inspect` reports the current directory, Git branch, modified files,
recognized project files, and likely validation commands. `fiaca doctor` gives
the same workspace checks without printing the full Git status. These commands
are read-only: they do not execute the detected validation commands or modify
files.

## Read-only file tools

Fiaca can inspect text files without reading outside the current workspace:

```bash
fiaca files
fiaca read src/fiaca/workspace.py
fiaca find "SessionStore"
```

Markdown files are rendered automatically:

```bash
fiaca read README.md
fiaca read docs/MESSAGE_PATTERN.md --markdown
```

Assistant responses and assistant messages in session history use the same
renderer, so headings, lists, code blocks, tables, emphasis, and links remain
readable in the terminal.

The tools reject paths outside the workspace, sensitive files such as `.env`,
ignored dependency directories, binary files, and files larger than the read
limit. Search accepts regular expressions and limits its output.

## Saved sessions and search

Fiaca stores local sessions in `~/.fiaca/sessions.db`:

```bash
fiaca sessions
fiaca history <session-id>
fiaca search "provider authentication"
```

The database contains messages and action records, but never API keys. The
common message structure is documented in
[`docs/MESSAGE_PATTERN.md`](docs/MESSAGE_PATTERN.md).

## Read-only tasks

Ask Fiaca to analyze the current workspace with real file context:

```bash
fiaca task \
  --file src/fiaca/ui.py \
  --file docs/MESSAGE_PATTERN.md \
  "Read the current terminal UI and propose a visual direction."
```

Without `--file`, Fiaca includes the main project files that are available.
Before contacting the provider, it shows the selected files and asks for
approval. Use `--yes` only when that approval is intentional:

```bash
fiaca task --yes "Explain the current project architecture."
```

Tasks are read-only. Fiaca does not modify files or execute commands. The task,
selected context, and provider response are stored in the local session
database. The dashboard exposes the same flow as `[7] New read-only task`.

To retry a saved task with its original files and provider:

```bash
fiaca task --session <session-id>
```

From the dashboard, open the session under `[5] Sessions` and choose `c`.

## Next direction

The next increment should be read-only file tools and agent mode, not more
provider options:

1. select an explicit working directory;
2. provide limited tools to list and read files;
3. propose patches for approval before writing;
4. run tests only after confirmation;
5. record every action in the session.

This moves Fiaca toward an Open Code-style workflow without silently executing
commands or modifying the project.
