# Claude Data Recovery

Turn an official Claude data export into a private, searchable offline viewer and a portable Markdown archive.

Claude Data Recovery runs locally, uses only the Python standard library, and never uploads your conversations.

> [!IMPORTANT]
> Claude exports can contain private conversations, account details, memories, and extracted attachment text. Never commit your export or generated recovery output to GitHub.

## What it creates

- A single-file offline web viewer with full-text search and filters
- One Markdown file per conversation
- A normalized JSON archive
- Memory and project recovery notes
- A data-quality report with best-effort Unicode repair
- Optional account metadata and an appeal checklist for your own local use

## Supported export files

| File | Support |
| --- | --- |
| `conversations.json` | Conversation messages, structured content, tools, thinking blocks, attachments |
| `design_chats/*.json` | Best-effort recovery of Claude design chats |
| `memories.json` | Conversation and project memories |
| `projects/*.json` | Project metadata and instructions |
| `users.json` | Local account verification notes |

Only `conversations.json` is required.

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/MindLeap-AI-Labs/claude-data-recovery.git
cd claude-data-recovery

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

claude-data-recovery "/path/to/extracted/claude-export" \
  --output "./claude-recovery-output"
```

Then open:

```text
claude-recovery-output/index.html
```

You can also point the command directly at `conversations.json`:

```bash
claude-data-recovery "/path/to/conversations.json"
```

## 中文快速开始

这个工具会在本地解析 Claude 官方数据导出，生成可搜索的离线网页、逐条对话 Markdown、记忆导入文本和项目恢复资料。整个过程不会上传数据。

```bash
claude-data-recovery "/你的/Claude导出文件夹" -o "./恢复结果"
```

生成后，直接用浏览器打开 `恢复结果/index.html`。

## Output structure

```text
claude-recovery-output/
├── index.html
├── normalized_data.json
├── README_RECOVERY.md
├── memory_import.md
├── project_recovery.md
├── account_appeal.md
└── markdown/
    └── 2026-01-01_001_example_conversation_ab12cd34.md
```

## Privacy design

- No network requests
- No analytics or tracking
- No API keys
- No third-party Python dependencies
- Text is rendered safely instead of injecting exported HTML
- Common export filenames are excluded by `.gitignore`

The generated `index.html` embeds your recovered data so it can be opened offline. Treat that file as sensitive.

## Known limitations

- Anthropic does not publish a stable schema for every export field, so parsing is best-effort.
- Exported data cannot recreate the original Claude sidebar in another personal account.
- Some attachment binaries may not be present; extracted attachment text is preserved when available.
- Very large exports create a correspondingly large single HTML file.

## Development

```bash
python -m unittest discover -s tests -v
python -m claude_data_recovery tests/fixtures/sample_export -o /tmp/claude-recovery-demo
```

The test fixture is synthetic and contains no real user data.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Please never attach a real Claude export to an issue; provide a minimal synthetic fixture instead.

## Security

For privacy or security problems, follow [SECURITY.md](SECURITY.md). Do not disclose conversation exports in public issues.

## License

[MIT](LICENSE)

## Disclaimer

Claude Data Recovery is an independent community project by MindLeap AI Labs. It is not affiliated with, endorsed by, or sponsored by Anthropic. Claude and Anthropic are trademarks of Anthropic PBC.
