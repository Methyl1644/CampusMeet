# Desktop Tutorial And Content Migration

## Goal

Keep desktop business pages focused on actions and real campus content. Move general explanations, examples, operating instructions, and safety guidance into a dedicated tutorial module.

## Scope

- Add a desktop primary-navigation item named `教程` and a `/tutorial` route.
- Keep the existing five-item mobile bottom navigation unchanged in this phase.
- Remove site-authored explanatory copy from login, discovery, publishing, post detail, messages, team detail, profile, and supporting empty states.
- Preserve real business content: topic summaries and source material, post descriptions, AI extraction and match results, messages, team plans, risks, tags, statuses, counts, field labels, button labels, and user data.
- Preserve concise dynamic feedback required to understand an operation, such as `发送失败`, `保存成功`, and `必填项未完成`.
- Remove contextual safety prose from business pages and include it in the tutorial.

## Tutorial Structure

The desktop tutorial page uses the existing campus-publication design language and contains six unframed sections:

1. 注册与校园认证
2. 查找话题与活动
3. 标准标签与搜索
4. AI 辅助发布组队帖
5. 申请、消息与确认组队
6. 联系方式与安全

Each section contains the guidance removed from business pages. The tutorial is reference material, not a wizard, and introduces no new backend state or API.

## Desktop Navigation

- Use the Lucide `BookOpen` icon.
- Add `教程` after `消息` and before `我的` in the desktop navigation.
- Filter the tutorial item out of the mobile navigation so its current five-column geometry remains stable.
- Register `/tutorial` under the authenticated `MainLayout` route tree.

## Content Rules

- Page and section headings remain.
- Field labels, control labels, status labels, search result metadata, and validation outcomes remain.
- Long helper paragraphs, examples, slogans, onboarding sentences, safety reminders, and empty-state instructions move to the tutorial.
- Search inputs may retain a short functional placeholder such as `搜索`.
- Empty states retain only a concise title, without suggested next steps.
- Tooltips naming icon-only controls remain for accessibility.

## Verification

- Contract tests assert the desktop tutorial route and navigation item exist while mobile navigation remains five columns.
- Contract tests assert representative explanatory copy is absent from business pages and present in the tutorial.
- TypeScript and production build must pass.
- Browser QA covers the tutorial and representative desktop pages at 1440 x 900 with no overflow or console errors.

## Deferred

- Mobile tutorial navigation and mobile-specific content cleanup.
- Backend-managed tutorial content, progress tracking, or analytics.
