const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../../..');
const React = require(path.join(root, 'apps/web/node_modules/react'));
const { renderToStaticMarkup } = require(path.join(root, 'apps/web/node_modules/react-dom/server'));
const lucide = require(path.join(root, 'apps/web/node_modules/lucide-react'));
const names = ['Trophy', 'BadgeCheck', 'Users', 'Search', 'X', 'ChevronDown', 'ChevronRight', 'ArrowLeft', 'ArrowRight', 'SlidersHorizontal', 'MapPin', 'CalendarDays', 'Clock', 'Heart', 'Bookmark', 'FileText', 'ExternalLink', 'ShieldCheck', 'Building2', 'GraduationCap', 'Tag', 'Check', 'BookOpen', 'Code2', 'CircleDot', 'UserRound', 'Info', 'LockKeyhole', 'Flag', 'Bell', 'Image', 'CheckCircle2', 'Compass', 'MessageSquare', 'Send', 'Sparkles', 'ListTodo', 'Plus', 'Pencil', 'RotateCcw', 'Mail', 'CircleAlert', 'CheckCheck', 'LogIn', 'FolderKanban'];
const icons = Object.fromEntries(names.map(name => [name, renderToStaticMarkup(React.createElement(lucide[name], { size: 20, strokeWidth: 1.7, 'aria-hidden': true }))]));
const source = fs.readFileSync(path.join(__dirname, 'topic-and-invitation.template'), 'utf8');
const html = source.replace('/*ICON_DATA*/', `window.ICONS = ${JSON.stringify(icons)};`)
  .replace('/*DISCOVERY_SEARCH*/', fs.readFileSync(path.join(__dirname, 'discovery-search.cjs'), 'utf8'))
  .replace('/*COLLAB_STATE*/', fs.readFileSync(path.join(__dirname, 'prototype-state.cjs'), 'utf8'))
  .replace('/*PUBLISHING_STATE*/', fs.readFileSync(path.join(__dirname, 'publishing-state.cjs'), 'utf8'))
  .replace('/*WORKSPACE_CSS*/', fs.readFileSync(path.join(__dirname, 'collaboration-ui.css'), 'utf8'))
  .replace('/*PUBLISHING_CSS*/', fs.readFileSync(path.join(__dirname, 'publishing-ui.css'), 'utf8'))
  .replace('/*WORKSPACE_UI*/', fs.readFileSync(path.join(__dirname, 'collaboration-ui.js'), 'utf8'))
  .replace('/*PUBLISHING_UI*/', fs.readFileSync(path.join(__dirname, 'publishing-ui.js'), 'utf8'));
for (const match of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
const output = path.join(__dirname, 'topic-and-invitation.html');
fs.writeFileSync(output, html, 'utf8');
console.log(`Built and syntax-checked: ${output}`);
