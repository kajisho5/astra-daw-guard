# astra-daw-guard — Claude Code 実装ロードマップ

このファイルを最初から最後まで実行すること。
推測で機能を増やさない。各フェーズの完了条件を満たしてから次へ進む。

## 目的

GPT-6 Astra などのエージェントが DAW（Ableton / Reaper / Cubase / FL Studio）を操作するとき、次を防ぐ。

- ネットから MIDI / サンプルを無断取得する
- 生成物と既存素材を混ぜて黙る
- プロジェクトを勝手に上書き保存する
- Computer Use でウィンドウやレイアウトを壊す

操作そのものは既存の MCP / OSC に任せる。このリポジトリは **禁止事項・許可事項・検証報告** をエージェントに強制する層。

## 非目的（やらない）

- 新しい DAW を作らない
- Ableton LiveAPI ブリッジを再発明しない
- 自動作曲モデルを訓練しない
- Computer Use のスクリーンクリック自動化を実装しない
- 有料 MIDI 倉庫や著作権 MIDI のミラーを作らない

## 完了の定義（リポジトリ全体）

次が揃ったら v0.1。

- [ ] `SKILL.md` が単体でエージェントに読ませて使える
- [ ] `policy/deny.txt` と `policy/allow.txt` がある
- [ ] 作業後レポートのテンプレートがある
- [ ] 悪い例（無断 MIDI 取得）と良い例がある
- [ ] README が日本語で、何を防ぐリポジトリか 10 行以内で分かる
- [ ] コードはまだ無くてよい。ドキュメントだけで v0.1 は完成

---

## フェーズ 0 — 骨格（30分）

作るファイル:

```
astra-daw-guard/
  README.md
  AGENTS.md
  SKILL.md
  LICENSE          # MIT
  ROADMAP.md       # このファイルを残す
  policy/
    allow.txt
    deny.txt
    license-allowlist.txt
  checklists/
    before.md
    during.md
    after.md
  adapters/
    README.md
    reaper.md
    ableton.md
    cubase.md
    flstudio.md
  examples/
    good-run.md
    bad-run-midi-fetch.md
    bad-run-autosave.md
```

完了条件:

- 空ファイルを残さない。各ファイルに「何のためのファイルか」が書いてある
- `git init` はユーザーが既にやっている場合は触らない

---

## フェーズ 1 — ポリシーを短く固める（最重要）

### `policy/deny.txt`

1行1ルール。命令形。例外を書かない。最低これらを入れる。

```
Do not download .mid .midi .kar files without explicit user approval in this turn.
Do not scrape BitMidi, MIDIWorld, Free MIDI, or unnamed MIDI dump sites.
Do not treat "public domain" as proven unless the URL is on license-allowlist.txt.
Do not overwrite the open DAW project. Save As only, and only if the user asked.
Do not mix generated MIDI and imported material on one track without labeling source.
Do not minimize, move, or retile DAW windows.
Do not change display zoom, color theme, or key bindings.
Do not install plugins, pack content, or accept license dialogs.
Do not send the user's project file, stems, or unpublished songs to a remote URL except the model API already in use.
Do not run Computer Use if an MCP/OSC adapter is available for the same action.
```

### `policy/allow.txt`

```
Read the current set: tempo, time signature, track list, clip names, devices.
Generate new MIDI from scratch when the user asked to compose.
Write MIDI only into a new track named with prefix GEN-.
Save As to a new filename that includes a timestamp if the user asked to save.
Use MCP/OSC/ReaScript if already configured.
Fetch a file only when: user named the URL in this turn AND the host is on license-allowlist.txt.
Report sources after every run using checklists/after.md.
```

### `policy/license-allowlist.txt`

許可してよいホストだけ。コメント付き。

```
# Classical PD scores as MIDI, project-by-project check still required
mutopiaproject.org
# Explicitly CC0 sample host — still record the sample page URL
freesound.org
# User's own machine
file://
```

BitMidi や midiworld.com は **入れない**。

完了条件:

- deny が 8 行以上
- allowlist が 5 ホスト未満（狭い方が正しい）

---

## フェーズ 2 — SKILL.md を書く

エージェントが読む本体。200行以内。見出しはこの順で固定。

1. いつ使うか
2. 使わないとき
3. 優先順位（MCP > 読み取り > Computer Use）
4. 禁止
5. 許可
6. 実行プロトコル（before → during → after）
7. 報告フォーマット（コピー用）
8. DAW別の注意（各5行以内、詳細は adapters/）

報告フォーマットは必ずコードブロックで置く。

```text
DAW:
Adapter used: mcp | osc | computer-use | none
Tracks changed:
MIDI added:
  - track: 
    source: generated | user-provided | url
    url:
    license:
Saved: no | saved-as <filename>
Computer Use used: yes/no
Denied actions (what I refused):
Failures:
```

完了条件:

- 「ネットから MIDI を取る」が禁止として本文に明記されている
- 報告フォーマットが本文からコピーできる
- 英語でも日本語でもエージェントが従えるよう、ルール本文は英語、解説は日本語でも可。どちらかに統一するなら英語ルール + 日本語 README

推奨: **ルール文は英語**（Claude Code / Codex が安定して読む）。README と examples は日本語。

---

## フェーズ 3 — チェックリスト

### `checklists/before.md`

作業前にエージェントが自分に問う質問。

- 開いているプロジェクト名は何か
- ユーザーは保存を依頼したか
- 依頼は「作曲」か「既存曲の再現」か「編曲」か
- MCP/OSC は使えるか
- ネット取得の許可は今ターンの文章にあるか

1つでも「既存曲をネットから持って再現」なら、生成に切り替えろと書く。既存MIDIの無断取得はしない。

### `checklists/during.md`

1操作ごと。

- 今から変えるオブジェクトは何か
- それは上書きか追加か
- deny.txt に当たるか

当たったら操作せず、Denied actions に書く。

### `checklists/after.md`

フェーズ2の報告フォーマットをここにも置く。加えて人間向けの短い日本語要約欄を付ける。

完了条件:

- before の質問が Yes/No で答えられる
- after が SKILL.md と同じフォーマット

---

## フェーズ 4 — アダプタメモ（実装しない、手順だけ）

各 `adapters/*.md` に書くこと。ページあたり 40 行以内。

必須セクション:

- 公式または既存のエージェント向け入口（URL）
- このリポジトリが推奨する操作手段
- Computer Use でやってはいけない UI
- 保存ダイアログの扱い

既存入口の例（リンク切れなら「未確認」と書け。嘘のURLを作るな）:

- Ableton: codex-live-bridge / ableton-live-mcp / ableton-mcp-extension を列挙し、このガードを先に読めと書く
- Reaper: ReaScript / 自作 MCP が将来入る想定。今は「読み取りと新規トラック追加以外禁止」
- Cubase: API が弱い。Computer Use は保存・ウィンドウ操作禁止を強調
- FL Studio: 同様。Piano roll の直接クリックは失敗しやすいと書く

`adapters/README.md` には「ここは操作実装ではなく注意書き」と書く。

---

## フェーズ 5 — 実施例

### `examples/good-run.md`

架空の良いログ。ユーザーが「8小節のハウスのドラムを新規トラックに作って。保存しないで」と言った場合。

- GEN-drums トラックを追加
- MIDI は生成
- 保存していない
- 報告フォーマットが埋まっている

### `examples/bad-run-midi-fetch.md`

悪い例。エージェントが Mutopia 以外の MIDI 倉庫から有名曲 MIDI を落としてプロジェクトに置いた。

- どのルールに違反したか
- 正しい応答（拒否文）を併記

拒否文の例:

```
I can't fetch that MIDI from the open web. I can compose a new part in the same style, or use a file you provide.
```

### `examples/bad-run-autosave.md`

勝手に上書き保存した悪い例と、Save As に変える正しい例。

完了条件:

- 悪い例は「何が悪いか」が最初の5行で分かる

---

## フェーズ 6 — README.md（日本語）

構成固定。

1. このリポジトリは何か（5行）
2. 防ぐこと（箇条書き4つ）
3. やらないこと（箇条書き3つ）
4. Claude Code / Codex での使い方

使い方はこれ以上増やさない。

```text
このリポジトリを開いた状態で:

1. AGENTS.md と SKILL.md を読め
2. policy/deny.txt に当たる操作をするな
3. 作業後は checklists/after.md のフォーマットで報告しろ
```

5. v0.1 の範囲（ドキュメントのみ）
6. 後続（フェーズ7以降は未実装）

完了条件:

- 英語リポジトリ名でも README は日本語で読んで分かる
- インストール手順や npm を書かない（まだコードが無い）

---

## フェーズ 7 — まだやるな（v0.2 以降）

ロードマップに書いておくだけ。v0.1 では実装しない。

1. Reaper 読み取り専用 MCP（トラック一覧、テンポ）
2. ダウンロードしたファイルのライセンス記録用 `sources.json`
3. Computer Use の前に deny を機械チェックする小さな CLI
4. 日本語 / 英語の拒否メッセージ辞書

やりたくなっても v0.1 をマージしてから。

---

## Claude Code への実行指示

今このリポジトリ（または空ディレクトリ）で次をやれ。

1. フェーズ0のファイルをすべて作る
2. フェーズ1〜6をこの順で埋める
3. フェーズ7は README の「後続」に箇条書きするだけ
4. 新しいディレクトリ名を勝手に変えない（`astra-daw-guard`）
5. 依存パッケージを追加しない
6. テストコードを書かない
7. 完了したら変更ファイル一覧と、SKILL.md の行数を報告する

品質基準:

- ルールは短く、例外を増やさない
- 「便利だから」で allowlist を広げない
- 存在しない GitHub リポジトリを公式のつもりで書かない。不確かなら「コミュニティ製・自己責任」と書く
- 著作権でグレーな MIDI サイトを助けない
