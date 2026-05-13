# dataCreator4Openclaw

这个项目用于把 `SWEContextBench Lite` 中的 related tasks 转换为 `wosuzyb` 名下可直接使用的 GitHub 任务仓库。

核心目标是：每个 upstream 仓库在 `wosuzyb` 下只保留一个 active fork，通过切换 active repo 的名字、默认分支 commit 和 issue 内容，让它代表当前要测试的某一个 related task。

## 项目里有什么

- `SWEContextBench/`
  - SWEContextBench 数据和 Lite 子集。
  - `SWEContextBench/lite/related.jsonl` 是当前主要任务来源。
- `tools/swecontext_materializer/`
  - 物料化工具源码。
  - CLI 入口是 `tools.swecontext_materializer.cli`。
- `generated/swecontextbench-lite/`
  - 生成的 manifest、状态文件和本地 checkout。
  - `status.json` 记录每个 task 当前执行状态。
- `tests/swecontext_materializer/`
  - 工具的单元测试。
- `astropy/`
  - 本地 astropy 源码副本，用于前期验证和示例任务。

## 运行要求

需要本机具备：

- Python 3
- `git`
- GitHub CLI：`gh`
- 已登录 GitHub CLI：

```bash
gh auth status
```

登录账号需要有权限在 `wosuzyb` 下创建、fork、重命名和管理 public repositories。

如果要移动包含 GitHub Actions workflow 的 ref，token 通常需要 `workflow` scope。

## 核心概念

### related task

`SWEContextBench/lite/related.jsonl` 中每一行是一个 related task，常用字段包括：

- `instance_id`
- `repo`
- `base_commit`
- `problem_statement`

例如：

```text
astropy__astropy-15082
```

表示来自 `astropy/astropy` 的一个任务。

### active repo

因为 GitHub 限制同一个 owner 对同一个 upstream 只能有一个 fork，所以本项目不再为 99 个 related task 同时创建 99 个 fork。

当前使用的方式是：

```text
每个 upstream repo 在 wosuzyb 下同一时间只有一个 active fork
```

切换任务时，工具会把这个 active fork 改造成目标 task 的状态。

### 仓库命名规则

active repo 名称格式是：

```text
<upstream-repo-name>-<task-number>
```

例子：

```text
astropy__astropy-15082              -> wosuzyb/astropy-15082
django__django-11776                -> wosuzyb/django-11776
scikit-learn__scikit-learn-12622    -> wosuzyb/scikit-learn-12622
```

## 常用命令

### 生成 manifest

```bash
python3 -m tools.swecontext_materializer.cli prepare-manifest
```

成功后会生成：

```text
generated/swecontextbench-lite/manifest.jsonl
```

预期输出类似：

```text
planned_tasks=99
output=generated/swecontextbench-lite/manifest.jsonl
```

### 查看状态

```bash
python3 -m tools.swecontext_materializer.cli status
```

状态文件位置：

```text
generated/swecontextbench-lite/status.json
```

### dry-run 激活任务

不会写 GitHub，只检查本地参数流程：

```bash
python3 -m tools.swecontext_materializer.cli activate-task \
  --instance-id astropy__astropy-15082 \
  --dry-run
```

### 真实激活任务

```bash
python3 -m tools.swecontext_materializer.cli activate-task \
  --instance-id astropy__astropy-15082
```

这会把 `astropy/astropy` 在 `wosuzyb` 下的 active fork 切换为：

```text
wosuzyb/astropy-15082
```

## activate-task 会做什么

执行：

```bash
python3 -m tools.swecontext_materializer.cli activate-task --instance-id <id>
```

工具会：

1. 从 manifest 中找到 `<id>` 对应的 task。
2. 根据 `instance_id` 计算目标仓库名。
3. 检查 `wosuzyb/<目标仓库>` 是否存在。
4. 如果目标仓库不存在：
   - 查找 `wosuzyb` 下是否已有同 upstream 的 fork。
   - 如果有，就重命名成目标仓库名。
   - 如果没有，就 fork upstream，再重命名。
5. 如果 GitHub redirect 导致目标名实际指向旧仓库名，工具会自动修正重命名。
6. 开启 issues。
7. 删除旧 open issues。
8. 关闭旧 open PRs，并删除本仓库中的 PR head branches。
9. 读取当前默认分支，默认分支可能是 `main`、`master` 或其他名字。
10. 把默认分支强制移动到 task 的 `base_commit`。
11. 删除除默认分支以外的所有 branches。
12. 删除所有 tags。
13. 用 task 的 `problem_statement` 创建新 issue。
14. 把结果写入 `generated/swecontextbench-lite/status.json`。

## 清理策略

默认清理策略是强清理：

```text
--cleanup-issues delete
--cleanup-prs close-and-delete-branches
```

可选参数：

```bash
--cleanup-issues none
--cleanup-issues delete

--cleanup-prs none
--cleanup-prs close
--cleanup-prs close-and-delete-branches
```

说明：

- issue 使用 GitHub GraphQL `deleteIssue` 删除。
- PR 无法通过 GitHub 常规 API 真正删除，所以工具会关闭 PR。
- 如果 PR 的 head branch 属于当前 `wosuzyb` 仓库，工具会删除该 branch。
- tags 会全部删除。
- branches 只保留仓库默认分支。

## 批量初始化 related upstream repos

`SWEContextBench/lite/related.jsonl` 里有 99 个 related tasks，来自 12 个 upstream repos。

如果想每个 upstream 选择一个 task 进行初始化，可以先生成选择列表。例如按 `repo` 分组后选择 `instance_id` 字典序最小的 task：

```bash
python3 - <<'PY'
import json
from collections import defaultdict
from pathlib import Path

by_repo = defaultdict(list)
for line in Path('SWEContextBench/lite/related.jsonl').read_text(encoding='utf-8').splitlines():
    row = json.loads(line)
    by_repo[row['repo']].append(row)

for repo in sorted(by_repo):
    task = sorted(by_repo[repo], key=lambda row: row['instance_id'])[0]
    print(task['instance_id'])
PY
```

然后逐个执行：

```bash
while read -r id; do
  [ -n "$id" ] || continue
  echo "=== activating $id ==="
  python3 -m tools.swecontext_materializer.cli activate-task --instance-id "$id"
done < selected_instances.txt
```

当前已经验证过的 12 个 active repos 包括：

```text
wosuzyb/astropy-15082
wosuzyb/django-11776
wosuzyb/matplotlib-10050
wosuzyb/seaborn-3091
wosuzyb/flask-4039
wosuzyb/requests-2344
wosuzyb/xarray-4529
wosuzyb/pylint-6471
wosuzyb/pytest-10341
wosuzyb/scikit-learn-12622
wosuzyb/sphinx-8127
wosuzyb/sympy-11275
```

## 网络重试

GitHub API 在大量删除 tags、branches 或 issues 时可能出现临时错误，例如：

- `EOF`
- `TLS handshake timeout`
- `SSL_ERROR_SYSCALL`
- `gnutls_handshake`
- `Connection reset by peer`
- `connection was non-properly terminated`

工具会对这些错误自动重试，降低长时间批处理因为单次网络抖动失败的概率。

如果某个 task 仍然失败，可以直接重跑同一个命令。工具会从当前远端状态继续清理和激活。

## 测试

运行完整测试：

```bash
uv run --with pytest pytest tests/swecontext_materializer -q
```

如果环境不能写默认 uv cache，可以指定临时 cache：

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --with pytest pytest tests/swecontext_materializer -q
```

## 注意事项

`activate-task` 会修改 GitHub 远端仓库，是破坏性操作：

- 会删除 open issues。
- 会关闭 open PRs。
- 会删除非默认分支。
- 会删除所有 tags。
- 会强制移动默认分支到指定 commit。
- 会重命名 active fork。

建议先 dry-run，再真实执行。

## 两阶段 linked task 切换

如果想先切到某个 related task 对应的一对一 experience task，再在下一条命令切回 related task，可以使用：

```bash
python3 -m tools.swecontext_materializer.cli activate-linked-task \
  --related-instance-id astropy__astropy-15082 \
  --phase experience
```

这会读取 `SWEContextBench/lite/related_relationship_links.tsv`，找到：

```text
astropy__astropy-15082 -> astropy__astropy-14995
```

然后把 active repo 切换到 experience task：

```text
wosuzyb/astropy-14995
```

下一步再运行：

```bash
python3 -m tools.swecontext_materializer.cli activate-linked-task \
  --related-instance-id astropy__astropy-15082 \
  --phase related
```

这会把同一个 upstream 的 active repo 切换到 related task：

```text
wosuzyb/astropy-15082
```

这个命令始终传入 related task 的 `instance_id`，通过 `--phase` 控制当前阶段：

- `--phase experience`：切到一对一关联的 experience task。
- `--phase related`：切到 related task 本身。

当前只支持一对一关系。如果一个 related task 对应多个不同 experience tasks，命令会报错并停止。

本项目暂不考虑“一个 related 对应多个 experience”的情况。原因是：当经验池需要由两个或多个历史任务共同构建时，如何组织、排序和使用这些经验仍存在不确定性，容易引入额外假设。因此当前实现只处理单个 related task 与单个 experience task 明确对应的一对一场景。
