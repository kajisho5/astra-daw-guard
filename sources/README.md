# sources/ — ライセンス記録の仕様

ROADMAP.md v0.2 の2番目の項目。`policy/allow.txt` が許可する範囲
（ユーザーが今のターンで名指ししたURL、かつホストが
`policy/license-allowlist.txt` にある場合のみ）でファイルを取得したとき、
その出典を機械可読な形で記録するための仕様です。

実際の記録先は、リポジトリ直下の `sources.json`（このディレクトリの中
ではありません）です。このディレクトリにはスキーマの説明と例だけを
置きます。

## スキーマ

`sources.json` は次の形のオブジェクトの配列です。

```json
[
  {
    "url": "https://mutopiaproject.org/ftp/.../piece.mid",
    "host": "mutopiaproject.org",
    "license": "Public Domain (Mutopia, see piece page for edition notes)",
    "fetched_at": "2026-09-06T22:30:00+00:00",
    "used_in_track": "GEN-piano-ref"
  }
]
```

| フィールド | 内容 |
|---|---|
| `url` | 実際に取得した完全なURL |
| `host` | URLのホスト名（`file://` の場合は `"file"`） |
| `license` | 確認したライセンス（人間が確認した内容をそのまま書く。自動判定しない） |
| `fetched_at` | 取得日時（ISO 8601, UTC） |
| `used_in_track` | 取り込んだ先のトラック名（無ければ `null`） |

サンプルは `sources.example.json` を参照してください。

## 記録の仕方

手で編集してもよいですが、`tools/record_source.py` を使うと
`policy/license-allowlist.txt` のホストチェック込みで追記できます。

```bash
python3 tools/record_source.py \
  --url "https://mutopiaproject.org/ftp/.../piece.mid" \
  --license "Public Domain (Mutopia)" \
  --track "GEN-piano-ref"
```

許可リスト外のホストは既定で拒否されます（`policy/deny.txt` の
「無断取得禁止」と同じ境界です）。

## 非目標

- ライセンスの自動判定はしません。あくまで人間/エージェントが確認した
  内容を記録するだけです。
- `sources.json` が無くても v0.1/v0.2 の他の機能は動きます。これは
  出典管理を後から追跡できるようにするための補助です。
