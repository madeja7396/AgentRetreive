了解。**「AgentRetrieve（エージェント向けgrep）」の“論文に耐えるベンチ”**として、今すぐ使える形で 4 点を埋めます（コーパス／タスク25件／ベースライン固定／実行制約）。

---

## 1) 評価用コーパス（リポジトリURL・固定コミット・ライセンス・主言語）

```yaml
# corpus.yaml
corpora:
  - id: ripgrep
    url: https://github.com/BurntSushi/ripgrep
    commit: af60c2d   # tag 15.1.0
    license: "Unlicense OR MIT"
    primary_language: "Rust"
    notes: "検索ツール本体。ignore/regex/CLI/benchが全部入ってる。"

  - id: fd
    url: https://github.com/sharkdp/fd
    commit: d38148f   # tag v10.3.0
    license: "Apache-2.0 OR MIT"
    primary_language: "Rust"
    notes: "find代替。エージェントが呼びがちな“探索”系の現実味。"

  - id: fzf
    url: https://github.com/junegunn/fzf
    commit: b908f7a   # tag v0.68.0
    license: "MIT"
    primary_language: "Go"
    notes: "候補列のフィルタリング＋環境変数地獄。エージェント相性が良い。"

  - id: curl
    url: https://github.com/curl/curl
    commit: 2eebc58   # tag curl-8_18_0
    license: "MIT-like"
    primary_language: "C"
    notes: "巨大C資産。docs/ src/ lib/ tests が揃ってて“現実の重さ”を出せる。"

  - id: fmt
    url: https://github.com/fmtlib/fmt
    commit: 407c905   # release 12.1.0
    license: "MIT"
    primary_language: "C++"
    notes: "ヘッダ群＋ベンチ＋実運用の塊。C++の“検索されがち”代表。"
```

根拠（固定コミット・主言語・ライセンス）: ripgrep 15.1.0 のタグ/コミット af60c2d と言語/ライセンス ([GitHub][1])、fd v10.3.0 のコミット d38148f と言語/ライセンス ([GitHub][2])、fzf v0.68.0 のコミット b908f7a と言語/ライセンス ([GitHub][3])、curl 8.18.0 のコミット 2eebc58 と言語/ライセンス ([GitHub][4])、fmt 12.1.0 のコミット 407c905 と言語/ライセンス ([GitHub][5])。

---

## 2) タスクセット（25件：クエリ＋正解 file/span-or-anchor）

**方針**：最初から「行番号スパン」を固定しようとすると、更新で壊れやすい。なので **gold を `file + anchor`（短い一致文字列）で定義**し、評価実装側で clone 後に anchor を検索して span を確定させるのが堅いです（論文で再現性が出る）。

```jsonl
{"id":"rg-01","repo":"ripgrep","query_nl":"ripgrepで .rgignore が .ignore より優先される説明はどこ？","query_dsl":{"must":[".rgignore","take precedence",".ignore"],"k":1},"gold":{"kind":"span","file":"GUIDE.md","anchor":".rgignore` globs, which take precedence over all `.ignore` globs"}}
{"id":"rg-02","repo":"ripgrep","query_nl":"ripgrepの -u/-uu/-uuu の挙動（unrestricted）説明はどこ？","query_dsl":{"must":["--unrestricted","-u","Repeated uses"],"k":1},"gold":{"kind":"span","file":"GUIDE.md","anchor":"ripgrep also provides a flag called `--unrestricted` (`-u` for short). Repeated uses of this flag"}}
{"id":"rg-03","repo":"ripgrep","query_nl":"ripgrepで結果順を安定させるオプションは？どこに書いてある？","query_dsl":{"must":["consistent order","--sort path"],"k":1},"gold":{"kind":"span","file":"FAQ.md","anchor":"You can achieve this with the `--sort path` flag"}}
{"id":"rg-04","repo":"ripgrep","query_nl":"ripgrepが圧縮ファイル検索に使うフラグは？","query_dsl":{"must":["--search-zip","gzip","bzip2"],"k":1},"gold":{"kind":"span","file":"FAQ.md","anchor":"ripgrep's `-z/--search-zip` flag will cause it to search compressed files"}}
{"id":"rg-05","repo":"ripgrep","query_nl":"ripgrepで man page を生成する方法は？","query_dsl":{"must":["--generate","man page","rg.1"],"k":1},"gold":{"kind":"span","file":"FAQ.md","anchor":"rg --generate man > man/man1/rg.1"}}

{"id":"fzf-01","repo":"fzf","query_nl":"fzfのbash統合（キーバインド/補完）を有効にする最短コマンドは？","query_dsl":{"must":["eval","fzf --bash","key bindings"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"eval \"$(fzf --bash)\""}}
{"id":"fzf-02","repo":"fzf","query_nl":"fzfの候補生成を差し替える環境変数は？（デフォルト挙動のoverride）","query_dsl":{"must":["FZF_DEFAULT_COMMAND","override the default behavior"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"Either by setting `$FZF_DEFAULT_COMMAND`"}}
{"id":"fzf-03","repo":"fzf","query_nl":"fzfのCTRL-R/ALT-Cなどのバインドを無効化する方法（環境変数で空にする）は？","query_dsl":{"must":["FZF_CTRL_R_COMMAND","FZF_ALT_C_COMMAND","empty string"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"You can disable CTRL-T, CTRL-R, or ALT-C bindings by setting"}}
{"id":"fzf-04","repo":"fzf","query_nl":"fzfをtmux popupで起動するオプション説明はどこ？","query_dsl":{"must":["--tmux","tmux popup"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"With `--tmux` option, fzf will start in a tmux popup"}}
{"id":"fzf-05","repo":"fzf","query_nl":"fzfでEnterを押したら別プロセスに置き換える（become）例は？","query_dsl":{"must":["become(","Turning into a different process"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"fzf --bind 'enter:become(vim {})'"}}

{"id":"curl-01","repo":"curl","query_nl":"curlが対応するプロトコル一覧はどこに書いてある？","query_dsl":{"must":["supports these protocols","DICT","HTTP","SFTP"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"It supports these protocols: DICT, FILE, FTP"}}
{"id":"curl-02","repo":"curl","query_nl":"curlのライセンスが“MIT-like”だという記述はどこ？","query_dsl":{"must":["MIT-like","license"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"curl is Open Source and is distributed under an MIT-like"}}
{"id":"curl-03","repo":"curl","query_nl":"curlのTHANKS（貢献者一覧）への導線はどこ？","query_dsl":{"must":["THANKS document","contributors"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"All contributors to the project are listed in"}}
{"id":"curl-04","repo":"curl","query_nl":"curlのソースコード取得（git clone）の行はどこ？","query_dsl":{"must":["git clone","https://github.com/curl/curl"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"git clone https://github.com/curl/curl"}}
{"id":"curl-05","repo":"curl","query_nl":"curlの脆弱性報告はどこ経由（HackerOne）？","query_dsl":{"must":["HackerOne","Report suspected security problems"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"Report suspected security problems via our HackerOne page"}}

{"id":"fmt-01","repo":"fmt","query_nl":"fmtの“最小構成は3ファイル”ってどの3つ？","query_dsl":{"must":["minimum configuration","base.h","format.h","format-inl.h"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"minimum configuration consisting of just three files, `base.h`, `format.h` and `format-inl.h`"}}
{"id":"fmt-02","repo":"fmt","query_nl":"fmtの浮動小数フォーマッタが使うアルゴリズム（Dragonbox）の記述は？","query_dsl":{"must":["Dragonbox","floating-point"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"Dragonbox"}}
{"id":"fmt-03","repo":"fmt","query_nl":"fmtをheader-onlyで使うときのマクロ名は？","query_dsl":{"must":["header-only","FMT_HEADER_ONLY"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"enabled with the `FMT_HEADER_ONLY` macro"}}
{"id":"fmt-04","repo":"fmt","query_nl":"fmtのcompile time / code bloat測定に使うスクリプト名は？","query_dsl":{"must":["bloat-test.py","code bloat"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"bloat-test.py"}}
{"id":"fmt-05","repo":"fmt","query_nl":"fmtベンチを走らせるために clone する別repo名は？","query_dsl":{"must":["format-benchmark","git clone --recursive"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"git clone --recursive https://github.com/fmtlib/format-benchmark.git"}}

{"id":"fd-01","repo":"fd","query_nl":"fdの“smart case”仕様（大文字が混ざると大小区別）説明はどこ？","query_dsl":{"must":["Smart case","case-insensitive","uppercase"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"Smart case: the search is case-insensitive by default. It switches to case-sensitive if the pattern contains an uppercase character"}}
{"id":"fd-02","repo":"fd","query_nl":"fdがデフォルトで隠しファイル/ディレクトリを無視する記述は？","query_dsl":{"must":["Ignores hidden","by default"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"Ignores hidden directories and files, by default."}}
{"id":"fd-03","repo":"fd","query_nl":"fdがデフォルトで .gitignore を尊重する記述は？","query_dsl":{"must":["Ignores patterns","`.gitignore`","by default"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"Ignores patterns from your `.gitignore`, by default."}}
{"id":"fd-04","repo":"fd","query_nl":"fdで隠しファイル検索を有効化するオプションは？","query_dsl":{"must":["-H","--hidden","disable this behavior"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"use the `-H` (or `--hidden`) option"}}
{"id":"fd-05","repo":"fd","query_nl":"fdをfzfの入力生成に使うときの推奨環境変数例は？","query_dsl":{"must":["export FZF_DEFAULT_COMMAND","fd --type file"],"k":1},"gold":{"kind":"span","file":"README.md","anchor":"export FZF_DEFAULT_COMMAND='fd --type file'"}}
```

タスクの根拠（アンカーが存在すること）: ripgrep GUIDE/FAQ/Cargo の該当記述 ([GitHub][6])、fzf README の該当記述 ([GitHub][7])、curl README の該当記述 ([GitHub][8])、fmt README の該当記述 ([GitHub][9])、fd README 該当箇所 ([GitHub][10])。

---

## 3) ベースライン条件（比較対象・バージョン固定）

最低ラインは「現状の現実（rg / git grep）＋競合（ugrep）＋古典（GNU grep）」で十分戦えます。

```yaml
# baselines.yaml
baselines:
  - tool: ripgrep
    version: 15.1.0
    cmd_template: "rg --no-heading --line-number --color never {pattern} {path}"

  - tool: git-grep
    version: 2.53.0
    cmd_template: "git grep -n --no-color {pattern} -- {path}"

  - tool: ugrep
    version: 7.5.0
    cmd_template: "ugrep -n --no-color {pattern} {path}"

  - tool: gnu-grep
    version: 3.11
    cmd_template: "grep -R -n --binary-files=without-match --color=never {pattern} {path}"
```

バージョン根拠: Git 2.53.0（Git for Windows の最新として 2026-02-02 リリース表記） ([Git][11])、GNU grep 3.11 の配布物 ([GNU FTP][12])、ugrep v7.5.0 ([GitHub][13])、ripgrep 15.1.0 ([GitHub][1])。

**固定方法（論文向け）**

* 依存を「OSパッケージ」に寄せない（勝手に上がって再現性が死ぬ）。
* `nix` / `mise` / `asdf` / Docker イメージのいずれかで **バイナリのハッシュまで固定**。
* 実験ログに `tool --version` を必ず保存。

---

## 4) 実行制約（OS/CPU/RAM・オフライン・許容レイテンシ）

```yaml
# run_constraints.yaml
environment:
  os: "Ubuntu 24.04 LTS (x86_64) または同等Linux"
  cpu: "8 cores 以上 (SMT込み可) / 例: Ryzen 7級 or Core i7級"
  ram: "32 GB 推奨 (最低16 GB)"
  storage: "NVMe SSD 推奨"
  offline: true   # 実行時ネットワーク遮断（DNSも落とす）

execution:
  cold_warm:
    - cold: "OS再起動 or ページキャッシュ破棄相当（可能なら）"
    - warm: "同一クエリを2回目実行（キャッシュ有り）"
  concurrency:
    threads: [1, "auto"]   # 単スレとデフォルト(並列)の両方を測る
  timeouts:
    per_query_sec: 10
    per_repo_sec: 600
  output_limits:
    max_hits: 2000   # 取り過ぎで比較が崩れるのを防ぐ

latency_targets:
  # “エージェントが気持ちよく回る”を数値化（まずはここを目標に置く）
  p50_ms: 50
  p95_ms: 200
  p99_ms: 500

reporting_must_include:
  - "uname -a"
  - "lscpu"
  - "free -h"
  - "lsblk (device/model)"
  - "各ツールの --version"
  - "クエリごとの wall/CPU time, RSS peak, read bytes"
```

**ポイント**：AgentRetrieve は「速い grep」だけじゃなく、エージェント観点だと **(1) 呼び出し回数**と **(2) 返すテキスト量（トークン量）**がコストになります。なので、ベンチには必ず

* `#calls`（タスク達成まで何回検索したか）
* `bytes_out`（結果出力の総バイト）
  を入れるのが、論文として強いです。

---

このセットは「最小の労力で、最大の再現性」を優先してあります。次の段階としては、タスクを **(A) symbol定義**, **(B) 仕様/設計ドキュメント**, **(C) エラーメッセージ**, **(D) 設定/環境変数** に層化して、難易度と出力量の分布を揃えると、Copernican感（“エージェント中心の評価軸”）が一気に濃くなります。

[1]: https://github.com/burntsushi/ripgrep/releases "Releases · BurntSushi/ripgrep · GitHub"
[2]: https://github.com/sharkdp/fd/releases "Releases · sharkdp/fd · GitHub"
[3]: https://github.com/junegunn/fzf/releases "Releases · junegunn/fzf · GitHub"
[4]: https://github.com/curl/curl/releases "Releases · curl/curl · GitHub"
[5]: https://github.com/fmtlib/fmt?utm_source=chatgpt.com "fmtlib/fmt: A modern formatting library"
[6]: https://raw.githubusercontent.com/BurntSushi/ripgrep/af60c2d/GUIDE.md "raw.githubusercontent.com"
[7]: https://raw.githubusercontent.com/junegunn/fzf/b908f7a/README.md "raw.githubusercontent.com"
[8]: https://raw.githubusercontent.com/curl/curl/2eebc58/README.md "raw.githubusercontent.com"
[9]: https://raw.githubusercontent.com/fmtlib/fmt/407c905/README.md "raw.githubusercontent.com"
[10]: https://github.com/sharkdp/fd/tree/d38148f "GitHub - sharkdp/fd at d38148f0aabdd073b4080cde770f679f3197b920"
[11]: https://git-scm.com/install/windows?utm_source=chatgpt.com "Git - Install for Windows"
[12]: https://ftp.gnu.org/gnu/grep/?utm_source=chatgpt.com "Index of /gnu/grep"
[13]: https://github.com/Genivia/ugrep/releases "Releases · Genivia/ugrep · GitHub"
