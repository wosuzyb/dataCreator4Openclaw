# SWEContextBench Lite 仓库生成计划、阻碍与后续路径

## 目标

我们想把 SWEContextBench Lite 里的 99 个 unique related task 生成到 `wosuzyb` 名下的 GitHub 仓库中。

每个 task 的目标形态是：

- 仓库名使用 `related_instance_id`，例如 `astropy__astropy-15082`。
- 仓库是 public。
- 仓库代码停在该 task 的 `base_commit`。
- 仓库必须保留原 upstream 的完整 commit history。
- 每个仓库创建一个 issue。
- issue 标题使用 `problem_statement` 的第一行。
- issue 正文只放完整 `problem_statement`，不追加任何 metadata。

## 数据来源

本地数据文件：

- `SWEContextBench/lite/related.jsonl`
  - 包含 99 个 related task。
  - 里面有 `instance_id`、`repo`、`base_commit`、`problem_statement`。
- `SWEContextBench/lite/related_relationship_links.tsv`
  - 包含 118 条 relationship row。
  - 但只有 99 个 unique `related_instance_id`。

当前计划按 `instance_id` / `related_instance_id` 去重，所以目标仍然是 99 个仓库。

## 已实现的本地工具

已经实现了一个 Python CLI：

- `tools/swecontext_materializer/`

它目前支持：

- 生成 manifest。
- 本地 clone / checkout。
- 创建 GitHub repo。
- push 代码。
- 创建 issue。
- 记录 status。
- dry-run 模式。

已验证：

- 单元测试 `16` 个通过。
- manifest 生成了正好 `99` 个 task。
- 前 2 个 task 的 dry-run 通过了 clone、创建 repo、push、创建 issue 这些阶段。

生成的 manifest 文件：

- `generated/swecontextbench-lite/manifest.jsonl`

## 重要发现：完整历史 push 太重

最开始的实现方式是：

1. 本地 clone upstream。
2. checkout 到 `base_commit`。
3. 在 `wosuzyb` 下创建一个空仓库。
4. 把本地 `main` push 到这个新仓库。

这个方法确实能保留 upstream history，但问题是它需要把 `base_commit` 可达的所有 Git objects 都上传到新仓库。

对 `astropy/astropy` 这种大仓库来说，这一步非常慢。实际测试时，push 长时间卡在：

- `git pack-objects`
- `git send-pack`

这说明如果对 99 个仓库都这样做，会非常慢，也很容易因为网络或 GitHub 限制失败。

## 已否定的替代方案：单提交快照

一个很快的替代方案是：

1. checkout upstream 到 `base_commit`。
2. 删除 `.git`。
3. 初始化一个新 git repo。
4. 把当前工作区内容 commit 成一个初始提交。
5. push 这个单提交仓库。

这个方法很快，也能保证文件内容完全等于 `base_commit` 时刻。

但这个方案已经被否定，因为我们明确要求：

```text
必须保留原 upstream 的完整 commit history
```

单提交快照不满足这个要求。

## 已测试的替代方案：远程 fork、移动 ref、rename

我们测试了一个远程优先的流程：

1. 删除半成品仓库 `wosuzyb/astropy__astropy-15082`。
2. fork `astropy/astropy` 到 `wosuzyb/astropy`。
3. 把 fork 的 `main` 移动到该 task 的 `base_commit`。
4. 把 `wosuzyb/astropy` rename 成 `wosuzyb/astropy__astropy-15082`。
5. 开启 issues。
6. 创建 task issue。

这个流程对单个 task 是成功的。

已验证仓库：

- `https://github.com/wosuzyb/astropy__astropy-15082`

已验证属性：

- 它是 `astropy/astropy` 的 fork。
- 它是 public。
- issues 已开启。
- `main` 指向目标 commit：
  - `c5e2521db013d9641999be9c79d1d807741bc39a`
- 已创建 issue `#1`，标题是：
  - `Bugfix for collapses with NDData without masks, or without units`

## 核心阻碍：GitHub 同一用户对同一 upstream 只能有一个 fork

在把 fork rename 成 `wosuzyb/astropy__astropy-15082` 之后，我们尝试再次 fork `astropy/astropy`。

GitHub 返回：

```text
wosuzyb/astropy__astropy-15082 already exists
```

这说明即使仓库已经 rename，GitHub 仍然认为它是 `wosuzyb` 对 `astropy/astropy` 的 fork。

因此这个循环不可行：

```text
fork upstream -> 移动 main -> rename -> 再 fork 同一个 upstream
```

这是一个关键阻碍，因为 SWEContextBench Lite 里同一个 upstream 会对应多个 task，例如：

- `django/django`：36 个 related task
- `sympy/sympy`：26 个 related task
- `matplotlib/matplotlib`：12 个 related task
- `scikit-learn/scikit-learn`：10 个 related task

也就是说，远程 fork + rename 不能用来批量生成 99 个独立仓库。

## 额外发现：token 需要 workflow 权限

移动 fork 分支到旧 commit 时，如果这个 ref update 涉及 `.github/workflows/...` 文件，GitHub 会要求 token 有 `workflow` scope。

遇到过的错误：

```text
refusing to allow a Personal Access Token to create or update workflow `.github/workflows/...` without `workflow` scope
```

后来给 `wosuzyb` 的 token 加了 `workflow` scope，这个问题已经解决。

当前 token 已包含：

- `repo`
- `workflow`
- `delete_repo`
- 其他 admin/user scopes

## problem_statement 中的历史引用

我们还扫描了：

- `SWEContextBench/lite/related.jsonl`

检查 `problem_statement` 里是否提到过往 PR、commit、compare URL 或其他历史上下文。

输出文件：

- `SWEContextBench/lite/problem_statement_history_refs.tsv`

扫描结果：

- 总共 99 个 task。
- 其中 34 个 task 明确或较强地提到了历史 PR、commit、compare URL 或 GitHub 历史引用。
- 30 个 task 有 PR-like 引用。
- 4 个 task 有 commit-like 引用。

例子：

- `astropy__astropy-15082`：引用了 `#14175`、`#14995`
- `django__django-30254`：引用了 commit `3e1e67021e0a20783ed59e17b43e3c481897fce3`
- `django__django-31504`：引用了 commit `290d8471bba35980f3e228f9c171afc40f2550fa`
- `sphinx-doc__sphinx-8127`：引用了 commit `661520c1442556016e328169c81c7cd3bdc7f7c3`
- `sympy__sympy-12950`：引用了 commit `6d55b862`

这说明有些 task 的 issue 文本确实依赖历史上下文。因此，保留完整 upstream history 对某些 agent 可能是有意义的。

## 后续可选路径

### 路径 1：每个 upstream 一个仓库，每个 task 一个分支

做法：

对每个 upstream repo 只 fork 一次，然后在这个 fork 里为每个 related task 创建一个分支。

例如：

- `wosuzyb/django`
  - branch `django__django-11776`
  - branch `django__django-18166`
  - branch `django__django-1891`
  - ...

优点：

- 保留完整 upstream history。
- 不需要重复上传大仓库历史。
- 符合 GitHub 的 fork 限制。
- 技术上最干净，也最快。

缺点：

- 不满足“99 个独立仓库”的原始要求。
- issue 需要都放在共享 fork 仓库里，或者用 issue 标题标识 task。

### 路径 2：坚持 99 个仓库，每个仓库完整历史 push

做法：

为每个 task 创建普通 GitHub repo，然后把 upstream 完整历史 push 进去，并把 `main` 指到对应 `base_commit`。

优点：

- 满足 99 个独立仓库。
- 保留完整 upstream history。
- 每个仓库可以有自己的唯一 issue。

缺点：

- 非常慢。
- 对 Django、SymPy、Astropy、Matplotlib、scikit-learn 这类大仓库尤其重。
- 需要很强的断点续跑和重试机制。
- 会消耗较多本地磁盘、网络带宽和 GitHub 存储。

### 路径 3：使用多个 GitHub owner

做法：

准备多个 GitHub 用户或 organization。因为 GitHub 的限制是“每个 owner 对每个 upstream 只能有一个 fork”，所以多个 owner 可以绕开单 owner 限制。

优点：

- 可以继续使用 GitHub fork 机制保留完整历史。
- 避免本地重复上传完整历史。
- 如果 owner 数量足够，仍然可以做到一个 task 一个仓库。

缺点：

- 运维复杂。
- 需要多个账号或组织。
- 权限、token、自动化管理都更麻烦。
- 不太推荐。

### 路径 4：放宽完整历史要求，使用单提交快照

做法：

为每个 task 创建一个新仓库，只保留 `base_commit` 时刻的文件内容，不保留原 upstream history。

优点：

- 快。
- 简单。
- 满足 99 个仓库。
- 每个仓库一个 issue。
- 文件状态精确等于 `base_commit`。

缺点：

- 不保留 upstream commit history。
- agent 无法在生成仓库内查看历史 commit。

这个路径目前已被否定，因为我们现在的要求是必须保留完整历史。

## 当前建议

在以下三个要求同时存在时：

- 99 个独立仓库
- 每个仓库保留完整 upstream commit history
- 只使用 GitHub 用户 `wosuzyb`

没有干净的 GitHub fork-based 方案。

目前技术上最干净的方案是路径 1：

```text
每个 upstream 一个 fork，每个 task 一个 branch
```

如果“99 个独立仓库”绝对不能变，那么只能走路径 2：

```text
99 个普通 repo，每个 repo 完整历史 push
```

但这会是一个慢任务，需要按长时间批处理来设计。

## 当前远端状态

已经创建并验证：

- `wosuzyb/astropy__astropy-15082`

这个仓库是从 `wosuzyb/astropy` rename 而来，仍然是 `astropy/astropy` 的 fork。

重要副作用：

- 因为它仍然被 GitHub 视为 `wosuzyb` 对 `astropy/astropy` 的 fork，所以在它存在期间，`wosuzyb` 不能再 fork `astropy/astropy`。

