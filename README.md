# kagent Slack bridge

Answers `@mentions` in Slack channels by calling a [kagent](https://kagent.dev)
agent over [A2A](https://github.com/google/A2A) and replying in the thread.
Bigabid runs it for Heimdall, the PM agent, in `#heimdall-pm-agent`
([DO-275](https://bigabid.youtrack.cloud/issue/DO-275)).

Forked from [kagent-dev/a2a-slack-template](https://github.com/kagent-dev/a2a-slack-template),
which answers a `/mykagent` slash command. The upstream repository has no license.

## Behaviour

- Listens for `app_mention` in the channels in `SLACK_CHANNELS`, reacts with
  :eyes: while it works, and answers in the thread.
- One agent session per Slack thread: the A2A `contextId` is
  `slack-<channel>-<thread_ts>`, so mentioning the bot again in the same thread
  continues the conversation.
- Posts only the last text part of the agent's answer (some models return
  their working as earlier parts), plus a token-usage line.
- Socket Mode: the bot connects out to Slack, nothing is exposed.

## Configuration

| Variable | Meaning |
| --- | --- |
| `SLACK_BOT_TOKEN` | Bot token (`xoxb-`) |
| `SLACK_APP_TOKEN` | App-level token (`xapp-`) with `connections:write` |
| `SLACK_CHANNELS` | Channel IDs to answer in, comma-separated |
| `KAGENT_A2A_URL` | The agent's A2A URL, `http://kagent-controller.kagent:8083/api/a2a/kagent/<agent>/` |
| `AGENT_DISPLAY_NAME` | Name used in error replies |
| `A2A_TIMEOUT_SECONDS` | Agent call timeout, default 600 |

Slack app: scopes `app_mentions:read`, `chat:write`, `reactions:write`; bot
event `app_mention`; Socket Mode on. The full manifest is in
`cloud-ops-toolkit/kagent-agents/CLAUDE.md`.

## Running locally

```bash
uv sync
uv run main.py   # reads .env
```

## Image

`.github/workflows/build.yaml` builds `linux/amd64` and `linux/arm64` on every
push and PR, and pushes to
`091546708236.dkr.ecr.us-east-1.amazonaws.com/kagent-slack-bridge` on `main`,
tagged with the commit SHA and a CalVer tag (`yymmdd-<run>`). The repository's
tags are immutable, so there is no `latest`. Dependencies are pinned in
`pyproject.toml` and `uv.lock`.
