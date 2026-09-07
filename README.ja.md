# astra-daw-guard

[![checks](https://github.com/kajisho5/astra-daw-guard/actions/workflows/checks.yml/badge.svg)](https://github.com/kajisho5/astra-daw-guard/actions/workflows/checks.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇬🇧 **English version: [README.md](README.md)**

AIエージェント（GPT-6 Astra、Codex、Claude Code など）が DAW を
操作するときに従うべき禁止事項・許可事項・作業後レポートのフォーマット
をまとめた、**AI Agent向けDAW safety / policy layer**です。特定のDAWの
MCPコレクションではありません。特定のDAWにも限定していません。
操作そのものは既存の MCP / OSC / Computer Use に任せ、このリポジトリは
その前後にかぶせる「やってよいこと・悪いこと」の層です。

これは**実際にデスクトップを操作できるエージェント**（画面をリアルタイムに
認識し、マウス・キーボードを直接操作するComputer Use機能を持つものも含む）
を前提に書いています。だからこそ`SKILL.md`の優先順位が重要になります:
その操作をMCP/OSCアダプタでできるならまずそれを使い、他に手段が無い場合
だけComputer Useに落とす。Computer Useは毎ターン画面をキャプチャして
読み直す必要があり、実際にトークンとレイテンシを消費し続ける上、
構造化された1回の呼び出しに比べて壊れやすい（ウィンドウ位置やズームが
変わるだけで通用しなくなる）ためです。この優先順位は建前ではなく、
使える場面では常に安く・確実な経路になります。

判定は2段構えです。`SKILL.md`をAgentに読ませて自然言語で守らせる層
（人間にも読める）と、`policy_engine/`という**機械可読なALLOW/ASK/DENY
判定エンジン**（構造化データのみを扱い、fail-closed）です。
`checklists/during.md`が操作ごとにこのエンジンを呼ぶ具体的な手順を、
`enforcement/`がTool実行そのものをこの判定でゲートする参照実装を
提供します。ただし、これは**Astra自身の実行中のAgent runtimeへの
実接続ではありません** — このリポジトリには実行中のAgentループが
存在しないため、呼び出し側（実際のAgent実行環境）がこれらをどう使う
かに委ねられています。「安全を保証する」ものではなく、「機械的に
判定・監査できる」層を提供するものです。

## 防ぐこと

- ネットから MIDI / サンプルを無断取得すること
- 生成物と既存素材を混ぜて出典を黙ること
- プロジェクトを勝手に上書き保存すること
- Computer Use で DAW のウィンドウやレイアウトを壊すこと

## やらないこと

- 新しい DAW や LiveAPI ブリッジを作ること
- 自動作曲モデルを訓練すること
- Computer Use のスクリーンクリック自動化を実装すること

## 対応DAW

ガードレール本体（`SKILL.md` / `policy/`）は全DAW共通で使えます。加えて、
一部のDAWにはMCPを同梱しており、テンポやトラック一覧を安全に取得
できます。ReaperとAbleton Liveには書き込みツール（トラック作成・
MIDI書き込み・ミキサー制御[volume/pan/mute/solo]・デバイスパラメータ
変更・トランスポート制御・テンポ変更・[Reaperのみ]別名保存）も
あります。Ableton Liveには保存ツールとInstrument Rackのチェーン
切り替えツールがありません — 経由先のAbletonOSC自体にそれらのOSC
アドレスが1つも存在しないことをソースコードで確認済みで、推測では
ありません。Ardourのみ読み取り専用のままです。書き込みツールは全て
上記のPolicy Engine / Enforcement Boundaryでゲートされています —
各ツールが正確に何をする・しないかは`mcp-reaper/README.md` /
`mcp-ableton/README.md`を参照してください。

| DAW | MCP | 書き込みツール | 経由するもの | 実機での動作確認 |
|---|---|---|---|---|
| Reaper | ✅ `mcp-reaper/` | ✅ トラック作成 / MIDI書き込み / 別名保存 | [reapy](https://github.com/RomeoDespres/reapy)（外部Pythonラッパー） | 未確認（ロジック検証のみ） |
| Ableton Live | ✅ `mcp-ableton/` | ✅ トラック作成 / MIDI書き込み / ミキサー / デバイスパラメータ / トランスポート / テンポ | [AbletonOSC](https://github.com/ideoforms/AbletonOSC)（Remote Script） | 未確認（擬似サーバーで検証済み） |
| Ardour | ✅ `mcp-ardour/` | 読み取り専用 | Ardour本体に内蔵のOSCサーフェス | 未確認（擬似サーバーで検証済み） |
| Bitwig Studio | ガードレールのみ（MCPなし） | — | 参考: [DrivenByMoss](https://github.com/git-moss/DrivenByMoss)のOSC機能（コミュニティ製・自己責任） | 未検証・未実装（`adapters/bitwig.md`） |
| FL Studio | ガードレールのみ（MCPなし） | — | 参考: [`flstudio-mcp`](https://github.com/rosasynthesiz/flstudio-mcp)（コミュニティ製・自己責任） | 未検証・未実装（`adapters/flstudio.md`） |
| Cubase | ガードレールのみ（MCPなし） | — | — | 調査済み: プラットフォーム側の制約で読み取り不可（`adapters/cubase.md`） |
| Pro Tools | ガードレールのみ（MCPなし） | — | — | 調査済み: EUCONはAvidパートナー限定で一般利用不可（`adapters/protools.md`） |
| Logic Pro | ガードレールのみ（MCPなし） | — | — | 調査済み: 読み取り可能なAPI/OSCなし（`adapters/logicpro.md`） |
| Studio One | ガードレールのみ（MCPなし） | — | — | 調査済み: 公開API/OSCなし（`adapters/studioone.md`） |
| Cakewalk | ガードレールのみ（MCPなし） | — | — | 調査済み: 公開API/OSCなし（`adapters/cakewalk.md`） |
| GarageBand | ガードレールのみ（MCPなし） | — | — | スクリプト機能自体が無い（`adapters/garageband.md`） |

ガードレール本体はどのDAWでも同じように使えます。MCPがあるのは今の
ところ Reaper・Ableton Live・Ardour の3つで、いずれも実機での疎通は
未検証です（擬似サーバーでのロジック検証は実施済み）。ReaperとAbleton
LiveのMCPには書き込みツールもあります（Issue #44、#46）。Ardourは
読み取り専用のままです。他のDAWは2026-09-07時点で個別に調査し、結果を
`adapters/*.md`に記録しています。誇張せず、調査済みで「無い」と
分かったものは「無い」と明記しています。

各アダプタの詳細・セットアップ手順は `mcp-reaper/README.md` /
`mcp-ableton/README.md` / `mcp-ardour/README.md` / `adapters/*.md` を
参照してください。3つとも `python3 install.py` で自動化できる部分は
自動化していますが、DAW側の設定変更（例: Ableton の Preferences で
Control Surface を選ぶ）は各アプリの外からは変更できないため手動です。
MCPのセットアップが不要な場合は、ガードレール本体（`SKILL.md` /
`policy/`）だけでも機能します。

## Astra など外部エージェントへの渡し方

このリポジトリの URL を渡すだけで使わせたい場合、次のように指示してください
（そのままコピー可）:

```text
このGitHubリポジトリを読んで、書かれたルールに従って作業してください:
https://github.com/kajisho5/astra-daw-guard

特に以下は必ず守ってください:
1. AGENTS.md と SKILL.md を読む
2. policy/deny.txt にある禁止事項を破らない
3. 作業後は checklists/after.md のフォーマットで報告する
```

エージェントがリポジトリ内を自分でたどれない場合に備えて、主要ファイルの
直リンクも渡しておくと確実です。

- ルール本体: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/SKILL.md
- 最優先の禁止事項: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/policy/deny.txt
- 許可事項: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/policy/allow.txt
- 報告フォーマット: https://raw.githubusercontent.com/kajisho5/astra-daw-guard/main/checklists/after.md

念のため、最低限守るべき禁止事項を`policy/deny.txt`の10行全てここにも
書いておきます（正本は `policy/deny.txt`。内容が食い違ったら
`policy/deny.txt` が優先）:

- ユーザーが今のターンで明示的に許可していない限り、ネットから
  `.mid` / `.midi` / `.kar` を取得しない
- BitMidi・MIDIWorld・Free MIDI など出所不明の MIDI 倉庫サイトからは
  取得しない
- 「パブリックドメイン」という表示だけでは信頼しない。ホストが
  `policy/license-allowlist.txt` に無ければ取得前に確認する
- 開いているプロジェクトファイルを上書き保存しない（保存する場合は
  必ず Save As、かつユーザーが保存を依頼した場合のみ）
- 生成したMIDIと外部から取り込んだ素材を、出典を書かずに同じトラックへ
  混ぜない
- DAW のウィンドウ位置・サイズを変更しない
- 表示倍率・配色テーマ・キー割り当てを変更しない
- プラグインのインストールやライセンスダイアログへの応答をしない
- プロジェクトファイル・ステム・未公開の楽曲を、このセッションで
  使っているモデルAPI以外へ送信しない
- MCP/OSC で同じ操作ができるなら Computer Use を使わない

全文は `policy/deny.txt`、実行手順は `SKILL.md` を参照してください。

## Claude Code / Codex での使い方

このリポジトリを開いた状態で:

1. AGENTS.md と SKILL.md を読め
2. policy/deny.txt に当たる操作をするな
3. 作業後は checklists/after.md のフォーマットで報告しろ

## 現在の状態

最新版は `v0.9.3.1`。Policy Engine（`policy_engine/`）・Enforcement
Boundary（`enforcement/`）ともに実装済み、テスト184件全通過。Reaperと
Ableton LiveにはPolicy Engineでゲートされた書き込みツールが追加
されました（Issue #44、#46）。詳しい開発の経緯は `CHANGELOG.md`、現状評価と
今後の方針は `ROADMAP.md` を参照してください。

正直な限界（誇張しません）: 実機DAWでの動作確認・実際のAstra Agent
runtimeへの結線は、いずれもこのリポジトリの中には存在しません。
理由と詳細は `ROADMAP.md` を参照。

## 貢献

このリポジトリ自体の開発に参加する場合は `CONTRIBUTING.md` を先に
読んでください。特に `policy_engine/` / `enforcement/` を変更する
PRは、独立したレビュー（`code-review`スキル等）を通すことを必須と
しています。

## ライセンス

[MIT License](LICENSE)
