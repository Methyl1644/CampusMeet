const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../../../..');
const React = require(path.join(root, 'apps/web/node_modules/react'));
const { renderToStaticMarkup } = require(path.join(root, 'apps/web/node_modules/react-dom/server'));
const lucide = require(path.join(root, 'apps/web/node_modules/lucide-react'));
const iconNames = [
  'Users', 'ShieldCheck', 'LockKeyhole', 'RotateCcw', 'LogIn', 'UserPlus', 'Mail',
  'KeyRound', 'ArrowRight', 'ArrowLeft', 'Check', 'Circle', 'BadgeCheck', 'Building2',
  'GraduationCap', 'Send', 'FileText', 'Clock3', 'CircleAlert', 'ExternalLink',
  'UserCog', 'CheckCircle2', 'XCircle', 'Eye', 'Compass', 'Info'
];
const icons = Object.fromEntries(iconNames.map(name => [
  name,
  renderToStaticMarkup(React.createElement(lucide[name], { size: 18, strokeWidth: 1.8, 'aria-hidden': true }))
]));

const read = name => fs.readFileSync(path.join(__dirname, name), 'utf8');
const html = read('auth.template')
  .replace('/*ICON_DATA*/', `window.ICONS = ${JSON.stringify(icons)};`)
  .replace('/*AUTH_STATE*/', read('auth-state.cjs'))
  .replace('/*AUTH_CSS*/', read('auth-ui.css'))
  .replace('/*AUTH_UI*/', read('auth-ui.js'));

for (const match of html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);

const output = path.join(__dirname, 'auth-prototype.html');
fs.writeFileSync(output, html, 'utf8');
console.log(`Built and syntax-checked: ${output}`);
