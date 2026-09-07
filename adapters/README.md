# adapters/

このディレクトリは操作実装ではなく注意書きです。
Each file here is notes on how an agent should approach a specific DAW —
what entry points exist, what this guard recommends, and what to never do
via Computer Use. None of these files contain code or a working
integration; they are read-first guidance for whichever MCP/OSC/Computer
Use tooling the user already has installed.

Files (✅ = this repo ships a read-only MCP for it; see the linked
`../mcp-*/` package):

- `reaper.md` ✅ `../mcp-reaper/`
- `ableton.md` ✅ `../mcp-ableton/`
- `ardour.md` ✅ `../mcp-ardour/`
- `bitwig.md` — community OSC bridge exists (DrivenByMoss), not wrapped here
- `cubase.md` — no read path found; platform limitation
- `flstudio.md` — community MCP exists (flstudio-mcp), not wrapped here
- `protools.md` — no read path found without an Avid partnership
- `logicpro.md` — no read path found
- `studioone.md` — no read path found
- `cakewalk.md` — no read path found
- `garageband.md` — no read path found (consumer app, no scripting)

Read `../SKILL.md` and `../policy/deny.txt` before using any of these.
