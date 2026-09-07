# astra-daw-guard

Astra / Codex / Claude Code が DAW を触る前に読むガードレール。

優先:
1. このリポジトリの `SKILL.md` と `policy/deny.txt` を先に読む
2. 今どのDAWを触るか確認し、`adapters/README.md` で該当ファイルを探して
   その `adapters/<name>.md` を読む（DAWごとに読み取り手段・禁止UIが
   違うため、これを飛ばさない）
3. 既存 MCP / OSC があればそれを使う。無ければユーザーに導入・設定を
   求めず、そのまま4番目に進む（`mcp-*/install.py` はユーザーが任意で
   使う道具であり、Astraが作業を止めてまで案内するものではない）
4. Computer Use は最後の手段
5. ネットから MIDI / サンプルを黙って取らない
6. プロジェクトを上書き保存しない
7. 作業後は `checklists/after.md` の報告フォーマットで出典を出す

このリポジトリを開発・拡張する場合（DAWを操作するAgentとして使う場合
ではなく）は、現在の実装状態・次フェーズ・未採用と判断した項目の
理由が `ROADMAP.md` に記録されているので、それを読むこと。
`ROADMAP.md` はもう「上から実行する構築手順書」ではなく、状況を記録
する文書になっている。
