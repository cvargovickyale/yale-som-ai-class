---
name: chatbot_dash
description: Build Dash chatbot applications with persistent message history, reliable submission controls, inline assistant replies, and a deliberately retro Windows Gateway 2000 visual style.
metadata:
  short-description: Build retro-styled, usable chatbot interfaces
---

# Chatbot UI

Use this skill when building a Dash web chat interface or adding chat behavior
to an existing application.

## Behavior

- Keep conversation history in application state and render the complete
  conversation in chronological order after each turn.
- Provide a clear multiline text box or input area, a visible Send button, and
  Enter-to-submit behavior. For multiline inputs, use Shift+Enter for a newline
  and Enter to submit; make the behavior discoverable in the UI.
- Disable submission while a request is in flight, show a compact working state,
  clear the submitted text from the input, and restore focus to the input after
  the reply arrives. The working state must be visually obvious even when a
  live-data or web-search call takes several seconds.
- Render user messages on the right and assistant messages on the left, like an
  iMessage-style conversation. Keep both readable at normal and narrow widths.
- Preserve the user’s message as submitted and show errors inline in the
  conversation area. Do not silently discard failed turns.
- Keep the latest messages visible by scrolling the conversation region, while
  leaving the input controls accessible.
- For Dash callbacks, use a loading wrapper or an equivalent visible pending
  state around the conversation, and return an empty input value after a
  successful submission so the submitted message is not mistaken for pending
  work.
- For multiline Dash textareas, implement a client-side keydown handler when
  needed: Enter submits by triggering the Send button, while Shift+Enter keeps
  its newline behavior. Do not rely only on `n_submit` if the browser does not
  consistently emit it for the chosen component.

## Visual direction

Use a Windows Gateway 2000 look without sacrificing modern usability:

- gray system panels, blue title bars, beveled borders, compact controls, and
  period-appropriate desktop UI details;
- readable system-style typography, strong focus states, and sufficient contrast;
- restrained decoration: the visual treatment should support scanning the chat,
  not obscure messages or status states;
- distinct message panels for user and assistant turns, with the alignment and
  hierarchy doing most of the work.

## Implementation guidance

- Match the project’s existing framework and dependency choices before adding
  new libraries.
- Separate message state, request handling, and presentation so the chat view
  remains easy to extend with tools, citations, streaming, or a reset action.
- Treat model/tool failures as normal UI states and provide a useful retry path.
- For live-data chatbots, label source freshness and citations where available;
  do not imply current information when a tool call failed or returned stale data.
- Follow the project’s `AGENTS.md` rules for secrets, local servers, and process
  cleanup. In particular, Dash apps must run without the auto-reloader/debug
  reloader and must be stopped by terminating the full process tree.
