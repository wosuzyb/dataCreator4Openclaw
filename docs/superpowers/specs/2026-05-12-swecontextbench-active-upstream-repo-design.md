# SWEContextBench Active Upstream Repo Design

## 目标

把 SWEContextBench Lite 的 related task 映射为 `wosuzyb` 账号下“每个 upstream 同一时间一个活跃仓库”的工作流。

这个设计替代“99 个 task 同时各一个 fork 仓库”的方案，因为 GitHub 限制同一 owner 对同一 upstream 只能有一个 fork。

## 核心模型

每个 upstream repo 同一时间只有一个活跃 repo。

活跃 repo 是 upstream 的 fork，保留完整 upstream commit history。

激活某个 task 时，脚本把对应 upstream 的活跃 repo 调整到该 task 状态：

- repo rename 成当前 task 名。
- `main` 强制移动到 task 的 `base_commit`。
- 删除旧 issue。
- 关闭旧 PR，并删除本仓库中的 PR head branch。
- 删除除 `main` 以外的所有分支。
- 删除所有 tag。
- 创建当前 task 的新 issue。

## 命名规则

目标 repo 名使用：

```text
<repo-name>-<task-number>
```

从 `instance_id` 解析：

```text
astropy__astropy-15082 -> astropy-15082
django__django-30153 -> django-30153
scikit-learn__scikit-learn-25365 -> scikit-learn-25365
```

如果目标 repo 已存在，脚本直接复用它，不报错，不重复创建。

## 输入

- `SWEContextBench/lite/related.jsonl`
  - 99 个 related task。
  - 使用字段：`instance_id`、`repo`、`base_commit`、`problem_statement`。
- `generated/swecontextbench-lite/manifest.jsonl`
  - 由现有工具生成。
  - 后续 `activate-task` 以 manifest 为 source of truth。

## `activate-task` 命令

建议命令：

```bash
python3 -m tools.swecontext_materializer.cli activate-task \
  --instance-id astropy__astropy-15082 \
  --cleanup-issues close \
  --cleanup-prs none
```

默认值：

```text
--cleanup-issues delete
--cleanup-prs close-and-delete-branches
```

可选值：

```text
--cleanup-issues none
--cleanup-issues delete

--cleanup-prs none
--cleanup-prs close
--cleanup-prs close-and-delete-branches
```

## 激活流程

给定 `instance_id`：

1. 从 manifest 读取 task。
2. 计算目标 repo 名，例如 `astropy-15082`。
3. 检查 `wosuzyb/<target-repo>` 是否存在。
4. 如果目标 repo 存在：
   - 直接复用它。
5. 如果目标 repo 不存在：
   - 查找 `wosuzyb` 下是否已经有该 upstream 的 fork。
   - 如果存在旧名字 fork，把它 rename 成目标 repo 名。
   - 如果不存在 fork，fork upstream，再 rename 成目标 repo 名。
6. 开启 issues。
7. 按 `--cleanup-issues` 处理旧 issue，默认删除所有 open issue。
8. 按 `--cleanup-prs` 处理旧 PR，默认关闭所有 open PR 并删除本仓库 head branch。
9. 删除除 `main` 以外的所有分支。
10. 删除所有 tag。
11. 强制移动 `main` 到 task 的 `base_commit`。
12. 创建新 issue：
    - title = `problem_statement` 第一行。
    - body = 完整 `problem_statement`。
11. 记录状态。

## 状态记录

状态文件继续放在：

```text
generated/swecontextbench-lite/status.json
```

每次 `activate-task` 记录：

- upstream repo，例如 `astropy/astropy`
- active repo，例如 `wosuzyb/astropy-15082`
- active `instance_id`
- active `base_commit`
- created issue number
- deleted issue numbers
- closed PR numbers
- deleted branch names
- deleted tag names
- cleanup options

## 清理策略

### Issue 清理

`--cleanup-issues delete`：

- 查询目标 repo 中所有 open issues。
- 使用 GitHub GraphQL `deleteIssue` 删除旧 issue。
- 然后创建当前 task 的新 issue。

`--cleanup-issues none`：

- 不关闭旧 issue。
- 直接创建当前 task issue。

### PR 清理

`--cleanup-prs none`：

- 不处理旧 PR。

`--cleanup-prs close`：

- 查询目标 repo 中所有 open PR。
- 关闭旧 PR。

`--cleanup-prs close-and-delete-branches`：

- 关闭旧 PR。
- 对 head repo 属于 `wosuzyb` 且 head branch 可删除的 PR，删除对应 branch。
- 不删除外部 contributor fork 的 branch。

PR 无法通过 GitHub 常规 API 真正删除，因此删除语义实现为关闭 PR，并删除本仓库可删除的 head branch。随后脚本会再删除除 `main` 以外的所有分支，确保仓库分支状态干净。

### 分支清理

无论 PR 清理选项如何，激活流程都会删除目标 repo 中除 `main` 以外的所有分支。若分支因保护规则或权限不足无法删除，命令失败并记录错误，避免静默留下旧任务状态。

### Tag 清理

激活流程会删除目标 repo 中所有 tag，避免旧 upstream 或旧任务 tag 影响当前任务上下文。若 tag 因权限或 API 错误无法删除，命令失败并记录错误。

## 错误处理

应停止并记录错误的情况：

- manifest 中找不到 `instance_id`。
- GitHub token 没有 `repo` 或 `workflow` 权限。
- upstream 不允许 fork。
- `base_commit` 在 fork 中不存在。
- rename 失败。
- ref update / push 失败。
- issue 创建失败。
- issue 删除失败。
- 非 `main` 分支删除失败。
- tag 删除失败。

## 已验证事实

对 `astropy__astropy-15082` 的 smoke test 已验证：

- fork `astropy/astropy` 到 `wosuzyb` 可行。
- 将 fork `main` 强制移动到 `base_commit` 可行，但 token 需要 `workflow` scope。
- rename fork 到 task repo 名可行。
- fork repo 默认可能关闭 issues，需要显式开启。
- 创建 issue 可行。
- rename 后不能再次 fork 同一个 upstream，因此必须采用“每个 upstream 同一时间一个活跃 repo”的模型。

## 成功标准

- `activate-task --instance-id <id>` 可以把对应 upstream 的活跃 repo 切换到指定 task。
- 目标 repo 名符合 `<repo-name>-<task-number>`。
- 目标 repo 是 upstream fork，保留完整 upstream history。
- `main` 指向 task 的 `base_commit`。
- 旧 issue 按开关删除。
- 旧 PR 按开关处理，默认关闭并清理本仓库 head branch。
- 除 `main` 以外的分支已删除。
- 所有 tag 已删除。
- 新 issue 标题和正文只来自 `problem_statement`。
- 重复运行同一个 `activate-task` 不会创建重复 repo。
