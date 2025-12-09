# Git 维护与同步指南 (Rebase 工作流版)

本文档记录了如何维护基于 `volcengine/verl` 的自定义修改版本。本指南采用 **Rebase（变基）** 策略，旨在保持提交历史整洁，并确保自定义功能始终基于官方最新代码运行。

## 1. 仓库架构说明

本仓库采用了 **Fork 工作流**，包含两个远程仓库地址：

*   **`origin` (我的仓库)**: 
    *   地址: `git@github.com:<你的用户名>/verl.git`
    *   作用: **读写**。用于保存我自己的修改、备份代码。
*   **`upstream` (官方仓库)**: 
    *   地址: `https://github.com/volcengine/verl.git`
    *   作用: **只读**。仅用于拉取（Fetch）官方的最新代码和 Bug 修复。

---

## 2. 首次配置（如果换了新环境）

如果你在一个新的环境克隆了代码，需要执行一次以下命令来配置远程关系：

```bash
# 1. 克隆自己的仓库
git clone git@github.com:<你的用户名>/verl.git
cd verl

# 2. 添加官方仓库作为上游 (upstream)
git remote add upstream https://github.com/volcengine/verl.git

# 3. 验证配置
git remote -v
# 输出必须包含 upstream 和 origin 两个远程仓库
```

---

## 3. 日常开发流程

### 场景 A：开发自己的功能

这是最常用的操作，流程如下：

1.  **修改代码**。
2.  **提交修改**：
    ```bash
    git add .
    git commit -m "feat: 添加了自定义的 reward 函数"
    ```
3.  **推送到自己的 GitHub**：
    ```bash
    git push origin main
    ```

### 场景 B：同步官方最新代码 (核心变更)

当官方 `verl` 发布了新版本，我们需要把官方修改“垫”在我们的修改下面。

1.  **确保工作区是干净的**（先提交或 stash 本地修改）：
    ```bash
    git status
    # 必须确保显示 "nothing to commit, working tree clean"
    ```

2.  **拉取官方最新更新**：
    ```bash
    git fetch upstream
    ```

3.  **执行变基 (Rebase)**：
    此命令的意思是：*“把我的修改暂时拿下来，把官方最新代码更新进来，然后再把我的修改应用到最顶端”*。
    ```bash
    git rebase upstream/main
    ```

4.  **处理可能出现的冲突**：
    *   **如果没有冲突**：Git 会直接提示成功，跳到第 5 步。
    *   **如果有冲突 (CONFLICT)**：
        1.  打开冲突文件，手动保留需要的代码（删除 `<<<<` `====` `>>>>` 标记）。
        2.  标记冲突已解决：
            ```bash
            git add .
            ```
        3.  继续变基过程（**注意：不要 commit，而是 continue**）：
            ```bash
            git rebase --continue
            ```
        4.  *如果在解决过程中搞乱了，想放弃本次同步，可以执行 `git rebase --abort` 回到原点。*

5.  **强制推送到自己的仓库**：
    由于 Rebase 修改了提交历史，普通的 `push` 会被拒绝，必须使用强制推送：
    ```bash
    git push -f origin main
    ```

6.  **更新 Python 环境（重要！）**：
    为了防止代码更新了但运行环境没更新（导致 import 的还是旧包），建议执行：
    ```bash
    pip install .
    # 或者如果之前用了 -e 模式安装，这一步通常可以省略，但为了保险建议重跑一次
    ```

---

## 4. 常见问题处理

### 报错：`refusing to merge unrelated histories`
如果在初次 Rebase 时遇到此错误，可以允许合并不相关的历史：
```bash
git rebase upstream/main --allow-unrelated-histories
```

### 报错：Lock file exists
如果 Git 崩溃导致无法操作，提示 `.lock` 文件已存在，执行以下命令清理：
```bash
find .git -name "*.lock" -exec rm -f {} \;
```

### 警告：系统时间检查
如果发现拉取的代码依然是旧的，或者 Git 行为怪异，请检查服务器系统时间：
```bash
date
# 如果时间不正确（例如显示是未来的时间），会导致构建工具误判文件未更新。
# 请务必校准时间后，再执行 pip install --force-reinstall .
```