# RAG-chat 开发文档

本目录包含 RAG-chat 项目的开发文档和工作流程指南。这些文档主要用于项目开发和维护，不是应用程序运行所必需的文件。

## 文档清单

- [DEVLOG.md](DEVLOG.md) - 开发日志，记录项目开发历程和里程碑
- [TASKS.md](TASKS.md) - 任务跟踪文档，列出待办、进行中和已完成的任务
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南，说明如何参与项目开发
- [WORKFLOW.md](WORKFLOW.md) - 工作流程指南，详细说明工作记录流程
- [TASK_TEMPLATE.md](TASK_TEMPLATE.md) - 任务模板，提供添加新任务的格式模板

## GitHub 模板

在 `docs/github_templates` 目录中，我们保存了 GitHub Issue 的模板文件：

- `bug_report.md` - Bug 报告模板
- `feature_request.md` - 功能请求模板

在实际部署时，这些模板应该被移动到 `.github/ISSUE_TEMPLATE` 目录中。

## 使用方法

1. 开发人员应该首先查看 `CONTRIBUTING.md` 了解项目的贡献规范
2. 使用 `TASKS.md` 跟踪开发任务和进度
3. 在 `DEVLOG.md` 中记录重要开发事件和完成的工作
4. 遵循 `WORKFLOW.md` 中描述的工作流程
5. 使用 `TASK_TEMPLATE.md` 作为添加新任务的模板

## 部署说明

在应用程序部署时，可以排除此目录，因为这些文档仅用于开发过程，不是应用程序运行所必需的。 