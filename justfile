set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

[doc("All command information")]
help:
    @just --list --unsorted

alias l := lint
[doc("Check and format code with autofix using ruff")]
[group("local")]
lint:
    uv run ruff format .
    uv run ruff check . --fix
    uv run ruff format .

alias tc := typecheck
[doc("Check types using pyrefly")]
[group("local")]
typecheck:
    uv run pyrefly check

alias b := bot
[doc("Run bot")]
[group("local")]
bot:
    uv run bot.py

alias r := rag
[doc("Run load documents into vector database")]
[group("local")]
rag:
    uv run rag.py